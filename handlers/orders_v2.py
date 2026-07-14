
from cfg import config
from utils import discord, ml, lib

from datetime import datetime
from zoneinfo import ZoneInfo
import holidays

def handle(data):
    res = data['resource'] #resource

    if data.get('debug', False) and config.DEBUG: print('Warning: Debug = True no post, pulando verificação do should_run')
    if data.get('debug', False) == False and lib.should_run(res) == False:
        return {'Status': 'OK'}, 200
    
    with discord.DiscordWebhook() as wh:
        wh.send(discord_format(res))
    return {'Status': 'OK'}, 200

def is_mute(): #verifica horario comercial / feriado / final de semana para mutar (role)
    agora = datetime.now(ZoneInfo('America/Sao_Paulo'))

    feriados_br = holidays.Brazil()

    fora_horario = agora.hour < 7 or agora.hour >= 18
    fim_de_semana = agora.weekday() >= 5  # 5=sábado, 6=domingo
    feriado = agora.date() in feriados_br

    return fora_horario or fim_de_semana or feriado

def is_new(det): #verifica se é novo ou se foi atualizado
    dt = datetime.fromisoformat(det['date_created'])
    return dt.date() == datetime.now(ZoneInfo("America/Sao_Paulo")).date()

def discord_format(res):
    det = ml.get(f'https://api.mercadolibre.com{res}') # detalhado

    item_details = [] # detalhado itens
    for order in det['order_items'][:10]:
        item = ml.get(f'https://api.mercadolibre.com/items/{order["item"]["id"]}')
        item_details.append(item)
        
    new = is_new(det)

    ship = ml.get(f'https://api.mercadolibre.com/shipments/{det["shipping"]["id"]}') #importante para o emoji

    #monta o venda_type (importante para role)
    mute = is_mute()
    venda_type = 'venda'
    if ship['logistic_type'] == 'fulfillment': venda_type = 'venda_full'
    elif mute: venda_type = 'venda_mute'

    pretext = f"{config.INFOS[venda_type]['role']} | **Nova venda realizada!**" if new else "**Venda atualizada?!**"

    emoji = f"(Missing Emoji: {ship['logistic_type']})"
    if ship['logistic_type'] in config.EMOJI_SHIP: emoji = config.EMOJI_SHIP[ship['logistic_type']]
    pretext += f" {emoji}"

    return {
        "content": f"{pretext} `{det['id']}`\n**R$ {det['total_amount']:,.2f}**\n{datetime.fromisoformat(det['date_created']).strftime('%d/%m/%Y %H:%M')}",
        "tts": False,
        "embeds": [
            {
            "description": "",
            "fields": [
                {
                "name": "ID:",
                "value": f"`{order['item']['id']}`",
                "inline": True
                },
                {
                "name": "SKU:",
                "value": f"`{order['item']['seller_sku']}`",
                "inline": True
                },
                {
                "name": "Estoque:",
                "value": f"`{item_det.get('available_quantity', '?')}`",
                "inline": True
                },
                {
                "name": "Valor:",
                "value": f"R$ {order['unit_price']:,.2f}/un (Total: R$ {order['unit_price']*order['quantity']:,.2f})"
                }
            ],
            "title": f"{order['quantity']}x {order['item']['title']}",
            "color": config.INFOS[venda_type]['color'],
            "url": f"https://produto.mercadolivre.com.br/MLB-{order['item']['id'].replace('MLB', '')}",
            "thumbnail": {
                "url": f"{item_det['thumbnail']}"
            }
            }
        
        for order,item_det in zip(det['order_items'][:9], item_details)
        ]+[
            {
            "id": 41287877,
            "description": "",
            "fields": [],
            "author": {
                "name": "ABRIR VENDA",
                "url": f"https://www.mercadolivre.com.br/vendas/{det['id']}/detalhe",
                "icon_url": config.INFOS[venda_type]['avatar_url']
            }
            }
        ],
        
        "components": [],
        "actions": {},
        "flags": 0,
        "username":  config.INFOS[venda_type]['username'],
        "avatar_url":  config.INFOS[venda_type]['avatar_url']
    }

    
