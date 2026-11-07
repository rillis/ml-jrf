from app import config, db
from app.handlers import Outcome, fmt_date


def find_sku(item):
    """SELLER_SKU tem prioridade; senão usa o primeiro MODEL."""
    sku = ''
    for att in item.get('attributes') or []:
        if att.get('id') == 'SELLER_SKU' and att.get('value_name'):
            return att['value_name']
        if att.get('id') == 'MODEL' and not sku:
            sku = att.get('value_name') or ''
    return sku


def handle(data, job, ml, now=None):
    res = data['resource']
    det = ml.get(res, params={'api_version': 4})
    item = ml.get(f"/items/{det['item_id']}")
    sku = find_sku(item)
    info = config.INFOS['pergunta']

    embed = {
        'title': item.get('title', ''),
        'color': info['color'],
        'url': f"https://produto.mercadolivre.com.br/MLB-{item['id'].replace('MLB', '')}",
        'fields': [
            {'name': 'ID:', 'value': f"`{item['id']}`", 'inline': True},
            {'name': 'SKU:', 'value': f'`{sku}`', 'inline': True},
            {'name': 'Texto:', 'value': det.get('text')},
        ],
    }
    if item.get('thumbnail'):
        embed['thumbnail'] = {'url': item['thumbnail']}

    payload = {
        'content': f"{info['role']} | **Nova pergunta!** `{det['id']}`\n{fmt_date(det.get('date_created'))}",
        'embeds': [
            embed,
            {
                'author': {
                    'name': 'ABRIR PERGUNTA',
                    'url': 'https://www.mercadolivre.com.br/perguntas/vendedor?page=1&period=15&sort=date_closed_asc&status=unanswered',
                    'icon_url': info['avatar_url'],
                },
            },
        ],
        'username': info['username'],
        'avatar_url': info['avatar_url'],
    }

    def history():
        db.execute(
            'INSERT INTO questions (content, item_id, post_time, res_id, sku) VALUES (%s, %s, now(), %s, %s)',
            (str(det.get('text') or ''), str(item['id']), res, str(sku)),
        )

    return Outcome(payload=payload, history=history)
