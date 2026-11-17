"""Endpoint que recebe as notificações do Mercado Livre e só enfileira."""
import json
import os
import threading
import time

from flask import Flask, g, request

from app import config, db, log
from app import queue as default_queue
from app.handlers import RECHECK_HANDLERS, route
from app.ml import MLClient, TokenInvalid

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


class TokenPing:
    """Confere o token com uma chamada leve ao ML; num 401 o MLClient renova.

    Pings seguidos (vários serviços tomando 401 juntos) esperam o primeiro e
    reaproveitam o resultado por PING_CACHE_SECONDS, sem chamar o ML de novo.
    """

    def __init__(self, ml=None, now=time.monotonic):
        self._ml = ml
        self._now = now
        self._lock = threading.Lock()
        self._last = None  # (quando, corpo, status)

    @property
    def ml(self):
        if self._ml is None:
            self._ml = MLClient()
        return self._ml

    def __call__(self):
        with self._lock:
            if self._last and self._now() - self._last[0] < config.PING_CACHE_SECONDS:
                return {**self._last[1], 'cache': True}, self._last[2]
            before = self.ml.tokens.read().get('token', '')
            try:
                self.ml.get('/users/me')
            except TokenInvalid as err:
                _logger.error(f'Ping: refresh token recusado pelo ML: {err}')
                result = {'status': 'token_invalido', 'renovado': False}, 503
            except Exception as err:  # noqa: BLE001
                _logger.warning(f'Ping: não consegui conferir o token: {err}')
                return {'status': 'erro', 'erro': str(err)[:300]}, 502  # erro passageiro não fica em cache
            else:
                renewed = self.ml.tokens.read().get('token', '') != before
                if renewed:
                    _logger.info('Ping: token renovado', extra={'color': log.GREEN})
                result = {'status': 'ok', 'renovado': renewed}, 200
            self._last = (self._now(), *result)
            return {**result[0], 'cache': False}, result[1]


def create_app(queue=default_queue, save_post_fn=None, token_ping=None):
    app = Flask(__name__)
    log.setup('web')
    save = save_post_fn or save_post
    ping = token_ping or TokenPing()

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

    @app.route('/token/ping', methods=['GET', 'POST'])
    def token_ping_view():
        if request.headers.get('CF-Connecting-IP'):  # só para a rede local, não pelo túnel
            return {'status': 'not_found'}, 404
        return ping()

    @app.get('/health')
    def health():
        problems = []
        body = {}
        try:
            body['fila'] = queue.health_stats()
            if body['fila']['atrasados'] and not os.path.exists(config.TOKEN_INVALID_FILE):
                problems.append(f"{body['fila']['atrasados']} notificação(ões) esperando há mais de 5 min")
        except Exception as err:  # noqa: BLE001
            problems.append(f'db: {err}')
        try:
            age = time.time() - os.path.getmtime(config.HEARTBEAT_FILE)
            body['worker_heartbeat_s'] = round(age)
            if age > config.HEARTBEAT_MAX_AGE:
                problems.append(f'worker parado há {age:.0f}s')
        except OSError:
            problems.append('worker sem heartbeat')
        body['token_ok'] = not os.path.exists(config.TOKEN_INVALID_FILE)
        if not body['token_ok']:
            problems.append('token do ML recusado: reautorize o app (fila pausada)')
        if problems:
            return {'status': 'unhealthy', 'problems': problems, **body}, 503
        return {'status': 'ok', **body}, 200

    return app
