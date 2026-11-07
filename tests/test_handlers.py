from datetime import datetime, timedelta

import pytest
from conftest import FakeML, fixture, notification

from app import config
from app.handlers import claims, debug, fmt_date, messages, orders, questions, route
from app.handlers.orders import is_mute

TZ = orders.TZ
WEEKDAY_WORK = datetime(2026, 11, 4, 10, 0, tzinfo=TZ)  # quarta, 10h


# ---------- roteamento ----------

@pytest.mark.parametrize('data, expected', [
    ({'topic': 'orders_v2'}, 'orders_v2'),
    ({'topic': 'messages'}, 'messages'),
    ({'topic': 'questions'}, 'questions'),
    ({'topic': 'items'}, None),
    ({'topic': 'post_purchase', 'actions': ['claims']}, 'claims'),
    ({'topic': 'post_purchase', 'actions': ['claims_actions']}, None),
    ({'topic': 'post_purchase', 'actions': []}, 'debug'),
    ({'topic': 'algo_novo'}, 'debug'),
])
def test_route(data, expected):
    assert route(data) == expected


def test_fmt_date_converte_para_sao_paulo():
    assert fmt_date('2026-11-04T08:28:55.000-04:00') == '04/11/2026 09:28'
    assert fmt_date('2026-11-07T14:39:48Z') == '07/11/2026 11:39'


# ---------- vendas ----------

def test_is_mute():
    assert not is_mute(WEEKDAY_WORK)
    assert is_mute(WEEKDAY_WORK.replace(hour=6))
    assert is_mute(WEEKDAY_WORK.replace(hour=18))
    assert is_mute(datetime(2026, 11, 7, 10, tzinfo=TZ))   # sábado
    assert is_mute(datetime(2026, 11, 20, 10, tzinfo=TZ))  # Consciência Negra (sexta)


def test_order_nova_venda(order_ml):
    ml, order = order_ml
    now = datetime.fromisoformat(order['date_created']) + timedelta(minutes=5)
    now = now.astimezone(TZ).replace(hour=10)  # dentro do horário comercial, mesmo dia
    out = orders.handle(notification('orders_v2', f"/orders/{order['id']}"), {}, ml, now=now)

    p = out.payload
    assert config.INFOS['venda']['role'] in p['content']
    assert 'Nova venda realizada!' in p['content']
    assert config.EMOJI_SHIP['xd_drop_off'] in p['content']
    assert 'atrasada' not in p['content']
    assert p['embeds'][0]['fields'][2]['value'] == '`82`'
    assert p['embeds'][-1]['author']['name'] == 'ABRIR VENDA'
    assert 'id' not in p['embeds'][-1] and 'components' not in p


def test_order_atrasada_continua_nova(order_ml):
    ml, order = order_ml
    now = datetime.fromisoformat(order['date_created']).astimezone(TZ) + timedelta(days=2)
    now = now.replace(hour=10)
    out = orders.handle(notification('orders_v2', f"/orders/{order['id']}"), {}, ml, now=now)
    assert 'Nova venda realizada!' in out.payload['content']
    assert '(notificação atrasada)' in out.payload['content']


def test_order_full_e_mute(order_ml):
    ml, order = order_ml
    ship_path = f"/shipments/{order['shipping']['id']}"
    ml.routes[ship_path] = {**ml.routes[ship_path], 'logistic_type': 'fulfillment'}
    now = datetime.fromisoformat(order['date_created']).astimezone(TZ).replace(hour=22)
    out = orders.handle(notification('orders_v2', f"/orders/{order['id']}"), {}, ml, now=now)
    assert config.INFOS['venda_full']['role'] in out.payload['content']

    ml.routes[ship_path] = {**ml.routes[ship_path], 'logistic_type': 'drop_off'}
    out = orders.handle(notification('orders_v2', f"/orders/{order['id']}"), {}, ml, now=now)
    assert config.INFOS['venda_mute']['role'] in out.payload['content']


def test_order_item_removido_nao_quebra(order_ml):
    ml, order = order_ml
    del ml.routes[f"/items/{order['order_items'][0]['item']['id']}"]
    out = orders.handle(notification('orders_v2', f"/orders/{order['id']}"), {}, ml, now=WEEKDAY_WORK)
    emb = out.payload['embeds'][0]
    assert emb['fields'][2]['value'] == '`?`'
    assert 'thumbnail' not in emb


def test_order_limita_9_itens(order_ml):
    ml, order = order_ml
    big = {**order, 'order_items': order['order_items'] * 12}
    ml.routes[f"/orders/{order['id']}"] = big
    out = orders.handle(notification('orders_v2', f"/orders/{order['id']}"), {}, ml, now=WEEKDAY_WORK)
    assert len(out.payload['embeds']) == 10
    assert ml.calls.count(f"/items/{order['order_items'][0]['item']['id']}") == 9


def test_order_history(order_ml, monkeypatch):
    ml, order = order_ml
    captured = []
    monkeypatch.setattr('app.db.execute', lambda sql, params=None: captured.append((sql, params)))
    out = orders.handle(notification('orders_v2', f"/orders/{order['id']}"), {}, ml, now=WEEKDAY_WORK)
    out.history()
    sql, params = captured[0]
    assert 'INSERT INTO orders_v2' in sql
    assert params[2] == f"/orders/{order['id']}" and params[3] == pytest.approx(33.1)


# ---------- mensagens ----------

def _message_ml():
    msg = fixture('message')
    res = msg['messages'][0]['id']
    return FakeML({f'/messages/{res}': msg, '/users/222222': fixture('user')}), res


def test_message():
    ml, res = _message_ml()
    out = messages.handle(notification('messages', res), {}, ml)
    p = out.payload
    assert 'Nova Mensagem!' in p['content'] and '07/11/2026 11:39' in p['content']
    assert p['embeds'][0]['title'] == 'Mensagem de COMPRADOR_TESTE - #2000019281004784'


def test_message_do_vendedor_e_pulada():
    ml, res = _message_ml()
    ml.routes[f'/messages/{res}']['messages'][0]['from']['user_id'] = 111111
    out = messages.handle(notification('messages', res), {}, ml)
    assert out.payload is None and 'vendedor' in out.note


# ---------- perguntas ----------

def test_question_sku():
    q = fixture('question')
    item = fixture('item')
    ml = FakeML({f"/questions/{q['id']}": q, f"/items/{q['item_id']}": item})
    out = questions.handle(notification('questions', f"/questions/{q['id']}"), {}, ml)
    assert out.payload['embeds'][0]['fields'][1]['value'] == '`KA-075`'
    assert questions.find_sku({'attributes': [{'id': 'MODEL', 'value_name': 'M1'}]}) == 'M1'
    assert questions.find_sku({'attributes': [{'id': 'MODEL', 'value_name': 'M1'},
                                              {'id': 'SELLER_SKU', 'value_name': 'S1'}]}) == 'S1'


# ---------- reclamações ----------

def _claim_ml():
    c = fixture('claim')
    res = f"/post-purchase/v1/claims/{c['id']}"
    return FakeML({
        res: c,
        f'{res}/messages': fixture('claim_messages'),
        f"/orders/{c['resource_id']}": fixture('claim_order'),
    }), res


def test_claim_alerta_e_alert_key():
    ml, res = _claim_ml()
    out = claims.handle(notification('post_purchase', res, actions=['claims']), {'alert_key': None}, ml)
    assert out.alert_key == '2'
    assert 'Produto Diferente ou Defeituoso' in out.payload['content']
    names = [f['name'] for f in out.payload['embeds'][1]['fields']]
    assert names == ['ML -> LOJA_TESTE', 'ML -> LOJA_TESTE']


def test_claim_sem_mensagens_novas_e_pulada():
    ml, res = _claim_ml()
    out = claims.handle(notification('post_purchase', res, actions=['claims']), {'alert_key': '2'}, ml)
    assert out.payload is None and out.alert_key == '2'


def test_claim_debug_ignora_alert_key():
    ml, res = _claim_ml()
    out = claims.handle(notification('post_purchase', res, actions=['claims'], debug=True), {'alert_key': '2'}, ml)
    assert out.payload is not None


def test_claim_papel_desconhecido_nao_quebra():
    ml, res = _claim_ml()
    ml.routes[f'{res}/messages'] = [{'sender_role': 'auditor', 'receiver_role': 'respondent', 'message': 'x'}]
    out = claims.handle(notification('post_purchase', res, actions=['claims']), {}, ml)
    assert out.payload['embeds'][1]['fields'][0]['name'] == 'auditor -> LOJA_TESTE'


def test_claim_de_outro_recurso_vai_para_debug():
    ml, res = _claim_ml()
    ml.routes[res] = {**ml.routes[res], 'resource': 'purchase'}
    out = claims.handle(notification('post_purchase', res, actions=['claims']), {}, ml)
    assert out.channel == 'debug'


def test_claim_via_shipment():
    ml, res = _claim_ml()
    c = ml.routes[res]
    ml.routes[res] = {**c, 'resource': 'shipment', 'resource_id': 555}
    ml.routes['/shipments/555'] = {'order_id': c['resource_id']}
    out = claims.handle(notification('post_purchase', res, actions=['claims']), {}, ml)
    assert out.payload is not None


def test_debug_handler():
    out = debug.handle({'topic': 'x', 'resource': 'y'}, {})
    assert out.channel == 'debug' and '"topic": "x"' in out.payload['embeds'][0]['description']
