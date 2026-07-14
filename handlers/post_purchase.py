from cfg import config
from utils import discord, ml, lib
from handlers import debug

from datetime import datetime

def handle(data):
    res = data['resource'] #resource

    if data.get('debug', False) and config.DEBUG: print('Warning: Debug = True no post, pulando verificação do should_run')
    
    with discord.DiscordWebhook() as wh:
        result_discord = wh.send(discord_format(res, data))
    if result_discord is None:
        return {'Status': 'Wrong Pattern or should not run (PP)'}, 400
    return {'Status': 'OK'}, 200

def discord_format(res_ori, data):
    det = ml.get(f"https://api.mercadolibre.com{res_ori}")
    if det['resource'] not in ('shipment', 'order'):
        debug.handle(data)
        return None
    
    id = det['id']
    res = det['resource']
    res_id = det['resource_id']

    msgs = ml.get(f'https://api.mercadolibre.com{res_ori}/messages')

    if data.get('debug', False) == False and lib.should_run(f'{res_ori}-{len(msgs)}') == False:
        return None

    if res == 'shipment':
        det_shipment = ml.get(f'https://api.mercadolibre.com/shipments/{res_id}')
        order = det_shipment['order_id']
    elif res == 'order':
        order = res_id

    det_order = ml.get(f'https://api.mercadolibre.com/orders/{order}')

    players = {}
    for player in det['players']:
        players[player['role']] = 'Cliente'
        if player['role'] == 'mediator': players[player['role']] = 'ML'
        elif player['user_id'] == config.SELLER_ID: players[player['role']] = config.CONTA
    
    tipo = f"({det['type']}?)"
    if det['type'] in config.POST_PURCHASE_DICT: tipo = config.POST_PURCHASE_DICT[det['type']]

    reason = '-'
    if det['reason_id'] is not None:
        if 'PDD' in det['reason_id']: reason = 'Produto Diferente ou Defeituoso'
        elif 'PNR' in det['reason_id']: reason = 'Produto Não Recebido'
        elif 'CS' in det['reason_id']: reason = 'Compra Cancelada'
        else: reason = f"{det['reason_id']}?"

    return {
        "content": f"{config.INFOS['reclamacao']['role']} | **Nova reclamação cadastrada!** `{id}`\n**Motivo:** {tipo} ({reason})\n{datetime.fromisoformat(det['date_created']).strftime('%d/%m/%Y %H:%M')}\n",
        "tts": False,
        "embeds": [
            {
                "description": "Informações da compra",
                "color": config.INFOS['reclamacao']['color'],
                "fields": [
                   {
                        "name": f"ID/SKU/Valor",
                        "value": f"`{o['item']['id']}` / `{o['item']['seller_sku']}` / R$ {o['unit_price']:,.2f}",
                        "inline": False
                    } 
                    for o in det_order['order_items'][:10]
                ]
            },

            {
                "description": "Mensagens (últimas 10)",
                "color": config.INFOS['reclamacao']['color'],
                "fields": [
                   {
                        "name": f"{players[msg['sender_role']]} -> {players[msg['receiver_role']]}",
                        "value": f"{msg['message'][:config.MAX_FIELD_SIZE-4]}"+'...' if len(msg['message'])>= config.MAX_FIELD_SIZE else msg['message'],
                        "inline": False
                    } 
                    for msg in msgs[-10:]
                ]
            },

            {
                "description": "",
                "fields": [],
                "author": {
                    "name": "ABRIR RECLAMAÇÕES",
                    "url": f"https://www.mercadolivre.com.br/post-purchase/post-sales?main.filter=problems-to-manage&history.filter=true#side-menu",
                    "icon_url": config.INFOS['reclamacao']['avatar_url']
                }
            }
        ],
        
        "components": [],
        "actions": {},
        "flags": 0,
        "username": config.INFOS['reclamacao']['username'],
        "avatar_url": config.INFOS['reclamacao']['avatar_url']
    }