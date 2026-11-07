from app import config, db
from app.handlers import Outcome, fmt_date


def handle(data, job, ml, now=None):
    res = data['resource']
    det = ml.get(f'/messages/{res}', params={'tag': 'post_sale'})

    msgs = det.get('messages') or []
    if not msgs:
        return Outcome.skip('mensagem sem conteúdo na API')
    msg = msgs[0]
    if msg['from']['user_id'] == config.SELLER_ID:
        return Outcome.skip('mensagem enviada pelo vendedor')

    user = ml.get_or_none(f"/users/{msg['from']['user_id']}") or {}
    nickname = user.get('nickname', str(msg['from']['user_id']))
    resources = msg.get('message_resources') or [{}]
    res_id = resources[0].get('id', '-')
    info = config.INFOS['mensagem']

    payload = {
        'content': f"{info['role']} | **Nova Mensagem!** `{msg['id']}`\n{fmt_date((msg.get('message_date') or {}).get('received'))}",
        'embeds': [
            {
                'title': f'Mensagem de {nickname} - #{res_id}',
                'color': info['color'],
                'fields': [{'name': 'Texto:', 'value': msg.get('text')}],
            },
            {
                'author': {
                    'name': 'ABRIR MENSAGEM',
                    'url': f'https://www.mercadolivre.com.br/vendas/novo/mensagens/{res_id}',
                    'icon_url': info['avatar_url'],
                },
            },
        ],
        'username': info['username'],
        'avatar_url': info['avatar_url'],
    }

    def history():
        db.execute(
            'INSERT INTO messages (message, post_time, res_id, user) VALUES (%s, now(), %s, %s)',
            (str(msg.get('text') or ''), str(res_id), nickname),
        )

    return Outcome(payload=payload, history=history)
