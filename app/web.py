"""Endpoint que recebe as notificações do Mercado Livre e só enfileira."""
import json
import os
import time

from flask import Flask, g, request

from app import config, db, log
from app import queue as default_queue
from app.handlers import RECHECK_HANDLERS, route

_logger = log.get('web')
_security = log.get('security')


def client_ip():
    return request.headers.get('CF-Connecting-IP') or request.remote_addr


def is_owner(data):
    """A notificação é da nossa conta e do nosso app?"""
    try:
        return int(data.get('user_id')) == config.SELLER_ID and int(data.get('application_id')) == config.APP_ID
    except (TypeError, ValueError):
        return False


def save_post(data):
    db.execute(
        'INSERT INTO posts (engine, post_time, url, content, topic, resource) VALUES (%s, now(), %s, %s, %s, %s)',
        (config.CONTA, request.host or '-', json.dumps(data, ensure_ascii=False),
         str(data.get('topic', '-')), str(data.get('resource', '-'))),
    )


def create_app(queue=default_queue, save_post_fn=None):
    app = Flask(__name__)
    log.setup('web')
    save = save_post_fn or save_post

    @app.before_request
    def _start():
        g.t0 = time.monotonic()

    @app.after_request
    def _access(resp):
        if request.path == '/health' and resp.status_code == 200:
            return resp  # healthcheck a cada 30s só poluiria o security.log
        ms = (time.monotonic() - g.get('t0', time.monotonic())) * 1000
        _security.info(f'{client_ip()} "{request.method} {request.path}" {resp.status_code} {ms:.0f}ms '
                       f'UA={request.headers.get("User-Agent", "-")!r}')
        return resp

    @app.post('/')
    def webhook():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data.get('topic') or not data.get('resource'):
            _security.warning(f'Rejeitado: corpo inválido de {client_ip()}: {request.get_data()[:300]!r}')
            _logger.warning(f'Rejeitado corpo inválido de {client_ip()}')
            return {'status': 'invalid'}, 400

        handler = route(data)
        topic, resource = data.get('topic'), data.get('resource')
        if handler is None:
            _logger.debug(f'Ignorado tópico {topic} {resource}')
            return {'status': 'ignored'}, 200

        if not is_owner(data):
            _security.warning(f'Ignorado: user_id/application_id não conferem, de {client_ip()}: {json.dumps(data)[:300]}')
            _logger.warning(f'Ignorado {topic} {resource}: user_id/application_id não conferem ({client_ip()})')
            return {'status': 'ignored'}, 200

        is_debug = bool(data.get('debug'))
        if is_debug:
            _logger.warning(f'debug=True no payload: deduplicação ignorada ({resource})')
        elif not config.ENSAIO:
            try:
                save(data)
            except Exception as err:  # noqa: BLE001 — log bruto não pode impedir o enfileiramento
                _logger.error(f'Falha ao gravar em posts: {err}')

        try:
            result = queue.enqueue(data, handler, is_debug=is_debug, recheck=handler in RECHECK_HANDLERS)
        except Exception as err:  # noqa: BLE001 — sem fila, pede para o ML reenviar
            _logger.error(f'Falha ao enfileirar {topic} {resource}: {err}')
            return {'status': 'unavailable'}, 503

        _logger.info(f'POST {topic} {resource}: {result}', extra={'color': log.BLUE})
        return {'status': 'queued', 'result': result}, 200

    @app.get('/health')
    def health():
        problems = []
        try:
            db.fetch('SELECT 1 AS ok')
        except Exception as err:  # noqa: BLE001
            problems.append(f'db: {err}')
        try:
            age = time.time() - os.path.getmtime(config.HEARTBEAT_FILE)
            if age > config.HEARTBEAT_MAX_AGE:
                problems.append(f'worker parado há {age:.0f}s')
        except OSError:
            problems.append('worker sem heartbeat')
        if problems:
            return {'status': 'unhealthy', 'problems': problems}, 503
        return {'status': 'ok'}, 200

    return app
