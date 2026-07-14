
from cfg import config
from utils import discord, ml, lib

from datetime import datetime

def handle(data):
    res = data['resource'] #resource

    if data.get('debug', False) and config.DEBUG: print('Warning: Debug = True no post, pulando verificação do should_run')
    if data.get('debug', False) == False and lib.should_run(res) == False:
        return {'Status': 'OK'}, 200
    
    with discord.DiscordWebhook() as wh:
        wh.send(discord_format(res))
    return {'Status': 'OK'}, 200

def discord_format(res):
    det = ml.get(f'https://api.mercadolibre.com{res}?api_version=4') #detalhado
    item = ml.get(f'https://api.mercadolibre.com/items/{det["item_id"]}') #item

    sku = ''
    for att in item['attributes']:
        if att['id'] == 'MODEL' and sku == '':
            sku = att['value_name']

        if att['id'] == 'SELLER_SKU':
            sku = att['value_name']
            break
    
    return {
        "content": f"{config.INFOS['pergunta']['role']} | **Nova pergunta!** `{det['id']}`\n{datetime.fromisoformat(det['date_created']).strftime('%d/%m/%Y %H:%M')}",
        "tts": False,
        "embeds": [
            {
            "description": "",
            "fields": [
                {
                "name": "ID:",
                "value": f"`{item['id']}`",
                "inline": True
                },
                {
                "name": "SKU:",
                "value": f"`{sku}`",
                "inline": True
                },
                {
                "name": "Texto:",
                "value": f"{det['text']}"
                }
            ],
            "title": f"{item['title']}",
            "color": config.INFOS['pergunta']['color'],
            "url": f"https://produto.mercadolivre.com.br/MLB-{item['id'].replace('MLB', '')}",
            "thumbnail": {
                "url": f"{item['thumbnail']}"
            }
            },
            {
            "description": "",
            "fields": [],
            "author": {
                "name": "ABRIR PERGUNTA",
                "url": f"https://www.mercadolivre.com.br/perguntas/vendedor?page=1&period=15&sort=date_closed_asc&status=unanswered",
                "icon_url": config.INFOS['pergunta']['avatar_url']
            }
            }
        ],
        "components": [],
        "actions": {},
        "flags": 0,
        "username": config.INFOS['pergunta']['username'],
        "avatar_url": config.INFOS['pergunta']['avatar_url']
    }
