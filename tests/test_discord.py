from app import discord
from app.discord import EMPTY_TEXT, sanitize


def test_trunca_limites():
    p = sanitize({
        'content': 'c' * 3000,
        'embeds': [{
            'title': 't' * 300,
            'description': 'd' * 5000,
            'fields': [{'name': 'n' * 300, 'value': 'v' * 1300}],
        }],
    })
    assert len(p['content']) == 2000 and p['content'].endswith('...')
    emb = p['embeds'][0]
    assert len(emb['title']) == 256 and len(emb['description']) == 4096
    assert len(emb['fields'][0]['name']) == 256 and len(emb['fields'][0]['value']) == 1024


def test_campo_vazio_vira_sem_texto():
    p = sanitize({'embeds': [{'fields': [{'name': '', 'value': ''}, {'name': 'a', 'value': None},
                                         {'name': 'b', 'value': '   '}]}]})
    assert [f['value'] for f in p['embeds'][0]['fields']] == [EMPTY_TEXT] * 3
    assert p['embeds'][0]['fields'][0]['name'] == '-'


def test_descricao_vazia_removida_e_original_intacto():
    original = {'embeds': [{'description': '', 'fields': []}]}
    p = sanitize(original)
    assert 'description' not in p['embeds'][0]
    assert original['embeds'][0]['description'] == ''


def test_maximo_10_embeds_e_25_campos():
    p = sanitize({'embeds': [{'fields': [{'name': 'a', 'value': 'b'}] * 30}] * 12})
    assert len(p['embeds']) == 10 and len(p['embeds'][0]['fields']) == 25


def test_ensaio_desliga_mencoes(monkeypatch):
    monkeypatch.setattr(discord.config, 'ENSAIO', True)
    assert sanitize({'content': 'x'})['allowed_mentions'] == {'parse': []}


class _Resp:
    def __init__(self, status, text=''):
        self.status_code = status
        self.text = text


class _Session:
    def __init__(self, status=204):
        self.status = status
        self.posts = []

    def post(self, url, json=None, timeout=None):
        self.posts.append((url, json))
        return _Resp(self.status, 'erro')


def test_sender_usa_canal_certo():
    s = _Session()
    discord.DiscordSender(session=s).send({'content': 'x'}, 'debug')
    assert s.posts[0][0] == 'https://discord.test/debug'


def test_sender_erro_levanta():
    import pytest
    with pytest.raises(RuntimeError):
        discord.DiscordSender(session=_Session(400)).send({'content': 'x'})
