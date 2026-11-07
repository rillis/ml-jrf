import json

from app import config
from app.handlers import HANDLERS, Outcome
from app.worker import Worker


class FakeQueue:
    def __init__(self, jobs=()):
        self.jobs = list(jobs)
        self.events = []

    def due(self, limit=20):
        jobs, self.jobs = self.jobs, []
        return jobs

    def claim(self, job_id):
        self.events.append(('claim', job_id))
        return True

    def finish(self, job_id, status, alert_key=None, note=''):
        self.events.append(('finish', job_id, status, alert_key))

    def retry_later(self, job_id, attempts, delay, error):
        self.events.append(('retry', job_id, attempts, delay))

    def fail(self, job_id, attempts, error):
        self.events.append(('fail', job_id, attempts))


class FakeDiscord:
    def __init__(self, error=None):
        self.sent = []
        self.error = error

    def send(self, payload, channel='main'):
        if self.error and channel == 'main':
            raise self.error
        self.sent.append((channel, payload))


def job(handler='orders_v2', attempts=0, **extra):
    return {'id': 7, 'handler': handler, 'topic': 'orders_v2', 'dedup_key': '/orders/1', 'attempts': attempts,
            'alert_key': None, 'payload': json.dumps({'topic': 'orders_v2', 'resource': '/orders/1'}), **extra}


def with_handler(monkeypatch, fn, name='orders_v2'):
    monkeypatch.setitem(HANDLERS, name, fn)


def test_sucesso_envia_conclui_e_grava_historico(monkeypatch):
    saved = []
    with_handler(monkeypatch, lambda d, j, ml: Outcome(payload={'content': 'x'}, history=lambda: saved.append(1)))
    q, d = FakeQueue([job()]), FakeDiscord()
    Worker(queue=q, ml=object(), discord=d).run_once()
    assert d.sent == [('main', {'content': 'x'})]
    assert ('finish', 7, 'done', None) in q.events and saved == [1]


def test_skip_nao_envia(monkeypatch):
    with_handler(monkeypatch, lambda d, j, ml: Outcome.skip('nada', alert_key='3'))
    q, d = FakeQueue([job()]), FakeDiscord()
    Worker(queue=q, ml=object(), discord=d).run_once()
    assert not d.sent and ('finish', 7, 'skipped', '3') in q.events


def test_falha_agenda_com_espera_crescente(monkeypatch):
    def boom(d, j, ml):
        raise RuntimeError('ML fora')
    with_handler(monkeypatch, boom)
    for attempts, delay in enumerate(config.RETRY_BACKOFF):
        q = FakeQueue([job(attempts=attempts)])
        Worker(queue=q, ml=object(), discord=FakeDiscord()).run_once()
        assert ('retry', 7, attempts + 1, delay) in q.events


def test_ultima_falha_marca_failed_e_avisa_debug(monkeypatch):
    with_handler(monkeypatch, lambda d, j, ml: Outcome(payload={'content': 'x'}))
    q = FakeQueue([job(attempts=len(config.RETRY_BACKOFF))])
    d = FakeDiscord(error=RuntimeError('Discord 400'))
    Worker(queue=q, ml=object(), discord=d).run_once()
    assert ('fail', 7, 6) in q.events
    assert d.sent[0][0] == 'debug' and 'falhou' in d.sent[0][1]['content']


def test_falha_no_historico_nao_reenvia(monkeypatch):
    def broken():
        raise RuntimeError('db')
    with_handler(monkeypatch, lambda d, j, ml: Outcome(payload={'content': 'x'}, history=broken))
    q, d = FakeQueue([job()]), FakeDiscord()
    Worker(queue=q, ml=object(), discord=d).run_once()
    assert ('finish', 7, 'done', None) in q.events and not any(e[0] == 'retry' for e in q.events)


def test_ensaio_nao_grava_historico(monkeypatch):
    saved = []
    monkeypatch.setattr(config, 'ENSAIO', True)
    with_handler(monkeypatch, lambda d, j, ml: Outcome(payload={'content': 'x'}, history=lambda: saved.append(1)))
    Worker(queue=FakeQueue([job()]), ml=object(), discord=FakeDiscord()).run_once()
    assert saved == []


def test_payload_dict_tambem_funciona(monkeypatch):
    got = []
    with_handler(monkeypatch, lambda d, j, ml: got.append(d) or Outcome.skip('ok'))
    Worker(queue=FakeQueue([job(payload={'resource': '/orders/1'})]), ml=object(), discord=FakeDiscord()).run_once()
    assert got == [{'resource': '/orders/1'}]
