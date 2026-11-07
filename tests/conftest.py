import json
import os
import tempfile
from pathlib import Path

import pytest

_TMP = tempfile.mkdtemp(prefix='ml-jrf-tests-')
os.environ.update({
    'ML_APP_ID': '999999',
    'ML_SELLER_ID': '111111',
    'ML_CONTA': 'LOJA_TESTE',
    'ML_SECRET_KEY': 'segredo',
    'DISCORD_WEBHOOK_URL': 'https://discord.test/main',
    'DISCORD_WEBHOOK_URL_DEBUG': 'https://discord.test/debug',
    'LOG_DIR': os.path.join(_TMP, 'logs'),
    'HEARTBEAT_FILE': os.path.join(_TMP, 'heartbeat'),
    'TOKENS_FILE': os.path.join(_TMP, 'tokens.json'),
    'ENSAIO': '0',
})

FIXTURES = Path(__file__).parent / 'fixtures'


def fixture(name):
    return json.loads((FIXTURES / f'{name}.json').read_text(encoding='utf-8'))


def notification(topic, resource, **extra):
    data = {
        '_id': 'abc-123', 'topic': topic, 'resource': resource,
        'user_id': 111111, 'application_id': 999999, 'attempts': 1, 'actions': [],
    }
    data.update(extra)
    return data


class FakeML:
    """Responde a partir das fixtures; caminhos ausentes viram 404."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, path, params=None):
        from app.ml import MLNotFound
        self.calls.append(path)
        if path not in self.routes:
            raise MLNotFound(404, path)
        value = self.routes[path]
        if isinstance(value, Exception):
            raise value
        return value

    def get_or_none(self, path, params=None):
        from app.ml import MLNotFound
        try:
            return self.get(path, params)
        except MLNotFound:
            return None


@pytest.fixture
def order_ml():
    order = fixture('order')
    item = fixture('item')
    return FakeML({
        f"/orders/{order['id']}": order,
        f"/items/{order['order_items'][0]['item']['id']}": item,
        f"/shipments/{order['shipping']['id']}": fixture('shipment'),
    }), order


@pytest.fixture
def no_db(monkeypatch):
    """Falha se algum código tentar usar o banco de verdade."""
    from app import db

    def boom(*a, **k):
        raise AssertionError('acesso ao banco não esperado')
    monkeypatch.setattr(db, 'execute', boom)
    monkeypatch.setattr(db, 'fetch', boom)
