from app import config, db
from app.handlers import Outcome, fmt_date
from app.handlers import debug as debug_handler

REASONS = (
    ('PDD', 'Produto Diferente ou Defeituoso'),
    ('PNR', 'Produto Não Recebido'),
    ('CS', 'Compra Cancelada'),
)


def reason_text(reason_id):
    if not reason_id:
        return '-'
    for prefix, text in REASONS:
        if prefix in reason_id:
            return text
    return f'{reason_id}?'


def handle(data, job, ml, now=None):
    res = data['resource']
    det = ml.get(res)
    if det.get('resource') not in ('shipment', 'order'):
        out = debug_handler.handle(data, job, ml)
        out.note = f"reclamação com resource {det.get('resource')!r}"
        return out

    msgs = ml.get(f'{res}/messages') or []
    alert_key = str(len(msgs))
    if not data.get('debug') and job.get('alert_key') == alert_key:
        return Outcome.skip('reclamação sem mensagens novas', alert_key=alert_key)

    res_id = det['resource_id']
    if det['resource'] == 'shipment':
        order_id = ml.get(f'/shipments/{res_id}')['order_id']
    else:
        order_id = res_id
    order = ml.get(f'/orders/{order_id}')

    players = {}
    for p in det.get('players') or []:
        if p.get('role') == 'mediator':
            players[p['role']] = 'ML'
        elif p.get('user_id') == config.SELLER_ID:
            players[p['role']] = config.CONTA
        else:
            players[p['role']] = 'Cliente'

    tipo = config.POST_PURCHASE_DICT.get(det.get('type'), f"({det.get('type')}?)")
    reason = reason_text(det.get('reason_id'))
    info = config.INFOS['reclamacao']

    payload = {
        'content': f"{info['role']} | **Nova reclamação cadastrada!** `{det['id']}`\n**Motivo:** {tipo} ({reason})\n{fmt_date(det.get('date_created'))}",
        'embeds': [
            {
                'description': 'Informações da compra',
                'color': info['color'],
                'fields': [
                    {
                        'name': 'ID/SKU/Valor',
                        'value': f"`{o['item']['id']}` / `{o['item'].get('seller_sku')}` / R$ {o['unit_price']:,.2f}",
                        'inline': False,
                    }
                    for o in order.get('order_items', [])[:10]
                ],
            },
            {
                'description': 'Mensagens (últimas 10)',
                'color': info['color'],
                'fields': [
                    {
                        'name': f"{players.get(m.get('sender_role'), m.get('sender_role'))} -> {players.get(m.get('receiver_role'), m.get('receiver_role'))}",
                        'value': m.get('message'),
                        'inline': False,
                    }
                    for m in msgs[-10:]
                ],
            },
            {
                'author': {
                    'name': 'ABRIR RECLAMAÇÕES',
                    'url': 'https://www.mercadolivre.com.br/post-purchase/post-sales?main.filter=problems-to-manage&history.filter=true#side-menu',
                    'icon_url': info['avatar_url'],
                },
            },
        ],
        'username': info['username'],
        'avatar_url': info['avatar_url'],
    }

    def history():
        db.execute(
            'INSERT INTO post_purchase (order_id, post_time, reason, res_id, type) VALUES (%s, now(), %s, %s, %s)',
            (str(order_id), reason, str(res_id), tipo),
        )

    return Outcome(payload=payload, history=history, alert_key=alert_key)
