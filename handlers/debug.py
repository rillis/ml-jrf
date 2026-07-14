
from cfg import config
from utils import discord

def handle(data):
    with discord.DiscordWebhook(debug_url=True) as wh:
        wh.send(discord_format(data))
    return {'Status': 'OK'}, 200

def discord_format(data, method='POST'):
    return {
        "username": config.INFOS['debug']['username'],
        "avatar_url": config.INFOS['debug']['avatar_url'],
        "content": f"{config.INFOS['debug']['role']} **{method} recebido!**",
        "embeds": [
            {
                "title": 'Conteúdo da Requisição:',
                "description": str(data),
                "color": config.INFOS['debug']['color'],
            }
        ]
    }
