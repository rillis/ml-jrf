import pytest
from conftest import notification

from app.web import create_app


class FakeQueue:
    def __init__(self, result='new', error=None):
        self.calls = []
        self.result = result
        self.error = error

    def enqueue(self, data, handler, is_debug=False, recheck=False):
        if self.error:
            raise self.error
        self.calls.append((data, handler, is_debug, recheck))
        return self.result


@pytest.fixture
def setup(no_db):
    q = FakeQueue()
    posts = []
    app = create_app(queue=q, save_post_fn=posts.append)
    return app.test_client(), q, posts


def test_valido_enfileira_e_grava_post(setup):
    client, q, posts = setup
    r = client.post('/', json=notification('orders_v2', '/orders/1'))
    assert r.status_code == 200 and r.json['status'] == 'queued'
    assert q.calls[0][1:] == ('orders_v2', False, False)
    assert len(posts) == 1


def test_reclamacao_usa_recheck(setup):
    client, q, _ = setup
    client.post('/', json=notification('post_purchase', '/post-purchase/v1/claims/1', actions=['claims']))
    assert q.calls[0][1] == 'claims' and q.calls[0][3] is True


@pytest.mark.parametrize('body', [b'', b'nao-json', b'[1,2]', b'{"topic": "orders_v2"}'])
def test_corpo_invalido_400(setup, body):
    client, q, _ = setup
    r = client.post('/', data=body, content_type='application/json')
    assert r.status_code == 400 and not q.calls


def test_form_nao_gera_415(setup):
    client, q, _ = setup
    r = client.post('/', data={'a': 'b'})
    assert r.status_code == 400


def test_topico_ignorado_200(setup):
    client, q, posts = setup
    r = client.post('/', json=notification('items', '/items/MLB1'))
    assert r.status_code == 200 and r.json['status'] == 'ignored'
    assert not q.calls and not posts


@pytest.mark.parametrize('extra', [{'user_id': 1}, {'application_id': 1}, {'user_id': None}])
def test_dono_errado_ignorado_200(setup, extra):
    client, q, _ = setup
    r = client.post('/', json=notification('orders_v2', '/orders/1', **extra))
    assert r.status_code == 200 and r.json['status'] == 'ignored' and not q.calls


def test_debug_nao_grava_post(setup):
    client, q, posts = setup
    client.post('/', json=notification('orders_v2', '/orders/1', debug=True))
    assert q.calls[0][2] is True and not posts


def test_curl_nao_e_mais_bloqueado(setup):
    client, q, _ = setup
    r = client.post('/', json=notification('orders_v2', '/orders/1'), headers={'User-Agent': 'curl/8.0'})
    assert r.status_code == 200


def test_fila_fora_responde_503(no_db):
    app = create_app(queue=FakeQueue(error=RuntimeError('db fora')), save_post_fn=lambda d: None)
    r = app.test_client().post('/', json=notification('orders_v2', '/orders/1'))
    assert r.status_code == 503


def test_falha_no_posts_nao_impede_fila(no_db):
    q = FakeQueue()

    def broken(_):
        raise RuntimeError('posts fora')
    app = create_app(queue=q, save_post_fn=broken)
    r = app.test_client().post('/', json=notification('orders_v2', '/orders/1'))
    assert r.status_code == 200 and q.calls


def test_get_raiz_405(setup):
    client, _, _ = setup
    assert client.get('/').status_code == 405


class HealthQueue(FakeQueue):
    def __init__(self, stats):
        super().__init__()
        self.stats = stats

    def health_stats(self):
        return self.stats


def _health(monkeypatch, tmp_path, stats, heartbeat=True, token_down=False):
    from app import config
    hb, flag = tmp_path / 'hb', tmp_path / 'flag'
    if heartbeat:
        hb.touch()
    if token_down:
        flag.touch()
    monkeypatch.setattr(config, 'HEARTBEAT_FILE', str(hb))
    monkeypatch.setattr(config, 'TOKEN_INVALID_FILE', str(flag))
    app = create_app(queue=HealthQueue(stats), save_post_fn=lambda d: None)
    return app.test_client().get('/health')


OK_STATS = {'pendentes': 0, 'processando': 0, 'falhas': 1, 'atrasados': 0}


def test_health_ok_com_resumo(monkeypatch, tmp_path):
    r = _health(monkeypatch, tmp_path, OK_STATS)
    assert r.status_code == 200 and r.json['fila']['falhas'] == 1 and r.json['token_ok'] is True


def test_health_fila_atrasada(monkeypatch, tmp_path):
    r = _health(monkeypatch, tmp_path, {**OK_STATS, 'atrasados': 3})
    assert r.status_code == 503 and 'esperando' in r.json['problems'][0]


def test_health_token_recusado(monkeypatch, tmp_path):
    r = _health(monkeypatch, tmp_path, {**OK_STATS, 'atrasados': 3}, token_down=True)
    assert r.status_code == 503 and r.json['token_ok'] is False
    assert len(r.json['problems']) == 1  # atraso por causa do token não conta duas vezes


def test_health_sem_heartbeat(monkeypatch, tmp_path):
    r = _health(monkeypatch, tmp_path, OK_STATS, heartbeat=False)
    assert r.status_code == 503 and 'heartbeat' in r.json['problems'][0]
