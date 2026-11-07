import json

import pytest
import requests

from app.ml import MLClient, MLError, MLNotFound


class Resp:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body if body is not None else {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class Session:
    def __init__(self, gets, post=None):
        self.gets = list(gets)
        self.post_resp = post
        self.get_headers = []
        self.posts = 0

    def get(self, url, headers=None, params=None, timeout=None):
        self.get_headers.append(headers['Authorization'])
        r = self.gets.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def post(self, url, headers=None, data=None, timeout=None):
        self.posts += 1
        return self.post_resp


@pytest.fixture
def tokens(tmp_path):
    path = tmp_path / 'tokens.json'
    path.write_text(json.dumps({'token': 'velho', 'refresh_token': 'TG-velho'}))
    return path


def client(tokens, session):
    return MLClient(tokens_file=tokens, app_id=1, secret='s', session=session, sleep=lambda s: None)


def test_ok(tokens):
    s = Session([Resp(200, {'a': 1})])
    assert client(tokens, s).get('/x') == {'a': 1}
    assert s.posts == 0


def test_401_renova_uma_vez_e_grava(tokens):
    s = Session([Resp(401), Resp(200, {'ok': True})],
                post=Resp(200, {'access_token': 'novo', 'refresh_token': 'TG-novo'}))
    assert client(tokens, s).get('/x') == {'ok': True}
    assert s.posts == 1
    assert s.get_headers == ['Bearer velho', 'Bearer novo']
    assert json.loads(tokens.read_text()) == {'token': 'novo', 'refresh_token': 'TG-novo'}
    assert not list(tokens.parent.glob('.tokens-*'))  # sem temporário sobrando


def test_401_persistente_nao_fica_em_loop(tokens):
    s = Session([Resp(401), Resp(401)], post=Resp(200, {'access_token': 'n', 'refresh_token': 'r'}))
    with pytest.raises(MLError):
        client(tokens, s).get('/x')
    assert s.posts == 1


def test_404_nao_renova_token(tokens):
    s = Session([Resp(404)])
    with pytest.raises(MLNotFound):
        client(tokens, s).get('/x')
    assert s.posts == 0
    assert client(tokens, Session([Resp(404)])).get_or_none('/x') is None


def test_429_e_500_tentam_de_novo(tokens):
    s = Session([Resp(429), Resp(503), Resp(200, {'ok': 1})])
    assert client(tokens, s).get('/x') == {'ok': 1}
    assert s.posts == 0


def test_desiste_apos_3_tentativas(tokens):
    s = Session([Resp(500), Resp(500), Resp(500)])
    with pytest.raises(MLError):
        client(tokens, s).get('/x')


def test_erro_de_rede_tenta_de_novo(tokens):
    s = Session([requests.ConnectionError('caiu'), Resp(200, {'ok': 1})])
    assert client(tokens, s).get('/x') == {'ok': 1}


def test_token_renovado_por_outro_processo_e_reaproveitado(tokens):
    s = Session([], post=Resp(500))
    c = client(tokens, s)
    tokens.write_text(json.dumps({'token': 'do-outro', 'refresh_token': 'TG-outro'}))
    assert c.refresh_token(used_token='velho') == 'do-outro'
    assert s.posts == 0


def test_log_nao_mostra_token(tokens, caplog):
    s = Session([Resp(401), Resp(200, {})],
                post=Resp(200, {'access_token': 'APP_USR-SEGREDO-1234', 'refresh_token': 'TG-SEGREDO-9876'}))
    import logging
    logger = logging.getLogger('ml-jrf')
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger='ml-jrf'):
            client(tokens, s).get('/x')
    finally:
        logger.propagate = False
    assert 'SEGREDO' not in caplog.text and '1234' in caplog.text


def test_refresh_recusado_vira_token_invalid(tokens):
    from app.ml import TokenInvalid
    s = Session([Resp(401)], post=Resp(400, {'error': 'invalid_grant'}))
    with pytest.raises(TokenInvalid):
        client(tokens, s).get('/x')


def test_refresh_com_erro_do_servidor_nao_e_token_invalid(tokens):
    from app.ml import TokenInvalid
    s = Session([Resp(401)], post=Resp(500))
    with pytest.raises(MLError) as exc:
        client(tokens, s).get('/x')
    assert not isinstance(exc.value, TokenInvalid)


def test_authorize_grava_tokens(tokens):
    s = Session([], post=Resp(200, {'access_token': 'A', 'refresh_token': 'R'}))
    client(tokens, s).authorize('CODE', 'https://exemplo/cb')
    assert json.loads(tokens.read_text()) == {'token': 'A', 'refresh_token': 'R'}
