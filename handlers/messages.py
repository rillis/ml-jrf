
from cfg import config
from utils import discord, ml, lib, db

from datetime import datetime

def handle(data):
    res = data['resource'] #resource

    if data.get('debug', False) and config.DEBUG: print('Warning: Debug = True no post, pulando verificação do should_run')
    if data.get('debug', False) == False and lib.should_run(res) == False:
        return {'Status': 'OK - Skip'}, 200
    
    with discord.DiscordWebhook() as wh:
        wh.send(discord_format(res))
    return {'Status': 'OK'}, 200

def save_on_db(message, res_id, user):
    with db.DBConnection() as conn:
        sql = "INSERT INTO messages (message, post_time, res_id, user) VALUES (%s, now(), %s, %s)"
        val = (str(message), str(res_id), str(user))
        conn.execute(sql, val=val)

def discord_format(res):
    det = ml.get(f'https://api.mercadolibre.com/messages/{res}?tag=post_sale') # detalhado

    msg = det['messages'][0]
    if msg['from']['user_id'] == config.SELLER_ID:
        if config.DEBUG: print('SKIP, mensagem respondida')
        return None

    user = ml.get(f"https://api.mercadolibre.com/users/{msg['from']['user_id']}")
    res_id = msg['message_resources'][0]['id']

    #saving
    save_on_db(msg['text'], res_id, user['nickname'])

    return {
        "content": f"{config.INFOS['mensagem']['role']} | **Nova Mensagem!** `{msg['id']}`\n{datetime.fromisoformat(msg['message_date']['received']).strftime('%d/%m/%Y %H:%M')}",
        "tts": False,
        "embeds": [
            {
            "description": "",
            "fields": [
                {
                "name": "Texto:",
                "value": f"{msg['text']}"
                }
            ],
            "title": f"Mensagem de {user['nickname']} - #{res_id}",
            "color": config.INFOS['mensagem']['color'],
            },
            {
            "description": "",
            "fields": [],
            "author": {
                "name": "ABRIR MENSAGEM",
                "url": f"https://www.mercadolivre.com.br/vendas/novo/mensagens/{res_id}",
                "icon_url": config.INFOS['mensagem']['avatar_url']
            }
            }
        ],
        "components": [],
        "actions": {},
        "flags": 0,
        "username": config.INFOS['mensagem']['username'],
        "avatar_url": config.INFOS['mensagem']['avatar_url']
    }

    
