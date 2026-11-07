"""Processa a fila: busca dados no ML, envia ao Discord e grava o histórico."""
import json
import signal
import time
import uuid
from pathlib import Path

from app import config, log
from app import queue as default_queue
from app.discord import DiscordSender
from app.handlers import HANDLERS
from app.handlers import debug as debug_handler
from app.ml import MLClient, TokenInvalid

_logger = log.get('worker')


class Worker:
    def __init__(self, queue=default_queue, ml=None, discord=None, sleep=time.sleep, now=time.time):
        self.queue = queue
        self.ml = ml or MLClient()
        self.discord = discord or DiscordSender()
        self._sleep = sleep
        self._now = now
        self.running = True
        self.token_down_since = None  # quando o refresh token começou a ser recusado
        self.paused_until = 0.0

    def process(self, job):
        """Processa um job já marcado como processing."""
        rid = uuid.uuid4().hex[:8]
        data = job['payload']
        if isinstance(data, (str, bytes)):
            data = json.loads(data)
        handler = HANDLERS[job['handler']]
        _logger.info(f"[{rid}] Processando {job['handler']} {job['dedup_key']} (fila #{job['id']})",
                     extra={'color': log.BLUE})
        try:
            outcome = handler(data, job, self.ml)
            if outcome.payload is not None:
                self.discord.send(outcome.payload, outcome.channel)
        except TokenInvalid as err:
            self._token_invalid(job, err, rid)
            return 'paused'
        except Exception as err:  # noqa: BLE001 — qualquer erro vira nova tentativa
            self._handle_failure(job, err, rid)
            return 'error'

        self._token_ok()
        status = 'done' if outcome.payload is not None else 'skipped'
        self.queue.finish(job['id'], status, alert_key=outcome.alert_key, note=outcome.note)
        if status == 'done':
            _logger.info(f"[{rid}] OK: alerta enviado ({outcome.channel})", extra={'color': log.GREEN})
        else:
            _logger.info(f"[{rid}] Pulado: {outcome.note}", extra={'color': log.GREEN})

        if outcome.history and not config.ENSAIO:
            try:
                outcome.history()
            except Exception as err:  # noqa: BLE001 — o alerta já foi; não reenviar por causa do histórico
                _logger.error(f'[{rid}] Falha ao gravar histórico: {err}')
        return status

    def _handle_failure(self, job, err, rid):
        attempts = int(job.get('attempts') or 0) + 1
        if attempts <= len(config.RETRY_BACKOFF):
            delay = config.RETRY_BACKOFF[attempts - 1]
            self.queue.retry_later(job['id'], attempts, delay, err)
            _logger.warning(f'[{rid}] Falha ({attempts}/{len(config.RETRY_BACKOFF)}), nova tentativa em {delay}s: {err}')
            return
        self.queue.fail(job['id'], attempts, err)
        _logger.error(f'[{rid}] Falhou de vez após {attempts} tentativas: {err}')
        try:
            self.discord.send(debug_handler.failure_payload({**job, 'attempts': attempts}, err), 'debug')
        except Exception as alert_err:  # noqa: BLE001
            _logger.error(f'[{rid}] Não consegui avisar no canal de debug: {alert_err}')

    def _token_invalid(self, job, err, rid):
        """Refresh token recusado: pausa a fila sem gastar tentativas e avisa uma vez só."""
        self.queue.retry_later(job['id'], int(job.get('attempts') or 0), config.TOKEN_PAUSE_SECONDS, err)
        self.paused_until = self._now() + config.TOKEN_PAUSE_SECONDS
        _logger.error(f'[{rid}] Token do ML recusado; fila pausada por {config.TOKEN_PAUSE_SECONDS}s: {err}')
        if self.token_down_since is not None:
            return
        self.token_down_since = self._now()
        self._set_token_flag(True)
        try:
            self.discord.send(debug_handler.token_invalid_payload(err), 'debug')
        except Exception as alert_err:  # noqa: BLE001
            _logger.error(f'[{rid}] Não consegui avisar no canal de debug: {alert_err}')

    def _token_ok(self):
        if self.token_down_since is None:
            return
        minutes = (self._now() - self.token_down_since) / 60
        self.token_down_since = None
        self._set_token_flag(False)
        _logger.info(f'Token do ML voltou a funcionar após {minutes:.0f} min; fila retomada', extra={'color': log.GREEN})
        try:
            self.discord.send(debug_handler.token_ok_payload(minutes), 'debug')
        except Exception as alert_err:  # noqa: BLE001
            _logger.error(f'Não consegui avisar no canal de debug: {alert_err}')

    @staticmethod
    def _set_token_flag(down):
        """Marca para o /health (outro processo) que o token está inválido."""
        path = Path(config.TOKEN_INVALID_FILE)
        try:
            if down:
                path.touch()
            elif path.exists():
                path.unlink()
        except OSError as err:
            _logger.warning(f'Não consegui atualizar {path}: {err}')

    def run_once(self):
        if self._now() < self.paused_until:
            return 0
        jobs = self.queue.due()
        for job in jobs:
            if not self.running:
                break
            self.heartbeat()  # um job pode levar minutos com a API do ML instável
            if self.queue.claim(job['id']) and self.process(job) == 'paused':
                break  # os demais ficam pendentes até o token voltar
        return len(jobs)

    def heartbeat(self):
        try:
            Path(config.HEARTBEAT_FILE).touch()
        except OSError as err:
            _logger.warning(f'Heartbeat falhou: {err}')

    def startup_check(self):
        try:
            me = self.ml.get('/users/me')
            _logger.info(f"API do ML OK: {me.get('nickname')} (app {config.APP_ID})", extra={'color': log.MAGENTA})
        except Exception as err:  # noqa: BLE001 — não derruba o container; a fila tenta de novo
            _logger.error(f'API do ML indisponível na partida: {err}')

    def run(self):
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)
        _logger.info(f'Worker iniciado (fila {config.QUEUE_TABLE}{", ENSAIO" if config.ENSAIO else ""})',
                     extra={'color': log.MAGENTA})
        self._set_token_flag(False)  # sinal de uma execução anterior não vale mais
        recovered = self.queue.recover_stuck()
        if recovered:
            _logger.warning(f'{recovered} job(s) presos em processing voltaram para pending')
        self.startup_check()
        while self.running:
            self.heartbeat()
            try:
                n = self.run_once()
            except Exception as err:  # noqa: BLE001 — banco fora, por exemplo
                _logger.error(f'Erro no laço do worker: {err}')
                n = 0
                self._sleep(10)
            if n == 0:
                self._sleep(config.WORKER_POLL_SECONDS)
        _logger.info('Worker encerrado')

    def _stop(self, *_):
        self.running = False


def main():
    log.setup('worker')
    Worker().run()


if __name__ == '__main__':
    main()
