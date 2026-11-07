from datetime import datetime, timedelta
from functools import lru_cache

import holidays

from app import config, db
from app.handlers import TZ, Outcome, fmt_date

MAX_ITEMS = 9  # 9 embeds de item + 1 de link = limite de 10 do Discord


@lru_cache(maxsize=1)
def _feriados():
    return holidays.Brazil()


def is_mute(now=None):
    """Fora do horário comercial, fim de semana ou feriado: usa o cargo silencioso."""
    now = now or datetime.now(TZ)
    return now.hour < 7 or now.hour >= 18 or now.weekday() >= 5 or now.date() in _feriados()


def handle(data, job, ml, now=None):
    now = now or datetime.now(TZ)
    res = data['resource']
    det = ml.get(res)

    items = det.get('order_items', [])[:MAX_ITEMS]
    item_details = [ml.get_or_none(f"/items/{o['item']['id']}") or {} for o in items]

    ship_id = (det.get('shipping') or {}).get('id')
    ship = (ml.get_or_none(f'/shipments/{ship_id}') or {}) if ship_id else {}
    logistic = ship.get('logistic_type')

    if logistic == 'fulfillment':
        venda_type = 'venda_full'
    elif is_mute(now):
        venda_type = 'venda_mute'
    else:
        venda_type = 'venda'
    info = config.INFOS[venda_type]

    emoji = config.EMOJI_SHIP.get(logistic, f'(Missing Emoji: {logistic})')
    pretext = f"{info['role']} | **Nova venda realizada!** {emoji}"

    created = datetime.fromisoformat(det['date_created'].replace('Z', '+00:00'))
    if now - created > timedelta(hours=config.LATE_NOTICE_HOURS):
        pretext += ' *(notificação atrasada)*'

    items_db = [f"{o['quantity']}x {o['item'].get('seller_sku')}" for o in items]
    total_db = sum(o['unit_price'] * o['quantity'] for o in items)

    payload = {
        'content': f"{pretext} `{det['id']}`\n**R$ {det['total_amount']:,.2f}**\n{fmt_date(det['date_created'])}",
        'embeds': [
            {
                'title': f"{o['quantity']}x {o['item'].get('title', '')}",
                'color': info['color'],
                'url': f"https://produto.mercadolivre.com.br/MLB-{o['item']['id'].replace('MLB', '')}",
                'thumbnail': {'url': d.get('thumbnail', '')},
                'fields': [
                    {'name': 'ID:', 'value': f"`{o['item']['id']}`", 'inline': True},
                    {'name': 'SKU:', 'value': f"`{o['item'].get('seller_sku')}`", 'inline': True},
                    {'name': 'Estoque:', 'value': f"`{d.get('available_quantity', '?')}`", 'inline': True},
                    {'name': 'Valor:', 'value': f"R$ {o['unit_price']:,.2f}/un (Total: R$ {o['unit_price'] * o['quantity']:,.2f})"},
                ],
            }
            for o, d in zip(items, item_details)
        ] + [
            {
                'author': {
                    'name': 'ABRIR VENDA',
                    'url': f"https://www.mercadolivre.com.br/vendas/{det['id']}/detalhe",
                    'icon_url': info['avatar_url'],
                },
            }
        ],
        'username': info['username'],
        'avatar_url': info['avatar_url'],
    }
    for emb in payload['embeds']:
        if 'thumbnail' in emb and not emb['thumbnail']['url']:
            del emb['thumbnail']

    def history():
        db.execute(
            'INSERT INTO orders_v2 (items, order_type, post_time, res_id, total_value) VALUES (%s, %s, now(), %s, %s)',
            (str(items_db), venda_type, res, float(total_db)),
        )

    return Outcome(payload=payload, history=history)
