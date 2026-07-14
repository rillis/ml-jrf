from cfg import private

# Debug mode
DEBUG = True

# General
TOKENS_FILE_PATH = 'cfg/tokens.json'
LOG_FILE_PATH = 'logs/recent.log'
MAX_LOG_SIZE = 10000

# listen config
IP = '0.0.0.0' #local
PORT = 80      #docker port

# mercado livre
APP_ID = private.APP_ID
CONTA = private.CONTA
SECRET_KEY = private.SECRET_KEY
SELLER_ID = private.SELLER_ID
ML_TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'

# connection mysql
DB_HOST = private.DB_HOST
DB_PORT = private.DB_PORT
DB_USER = private.DB_USER
DB_PASSWORD = private.DB_PASSWORD
DB_DATABASE = private.DB_DATABASE

# webhook
WEBHOOK_URL = private.WEBHOOK_URL
WEBHOOK_URL_DEBUG = private.WEBHOOK_URL_DEBUG
MAX_FIELD_SIZE = 1024

# message creators
_URLBASE_AVATARS = 'https://estoque.rillis.com.br/imgs/'

# dicts
INFOS = {
    'venda': {
        'username': 'ML Venda',
        'role': '<@&1398488993997258892>',
        'color': 0x1cfc03,
        'avatar_url': _URLBASE_AVATARS + 'venda.png',
    },
    'venda_mute': {
        'username': 'ML Venda',
        'role': '<@&1516278758494175314>',
        'color': 0x0a2c18,
        'avatar_url': _URLBASE_AVATARS + 'venda_mute.png',
    },
    'venda_full': {
        'username': 'ML Venda',
        'role': '<@&1501620909985890434>',
        'color': 0x1f8b4c,
        'avatar_url': _URLBASE_AVATARS + 'venda_full.png',
    },
    'mensagem': {
        'username': 'ML Mensagem',
        'role': '<@&1398489074779689023>',
        'color': 0x07e8f0,
        'avatar_url': _URLBASE_AVATARS + 'mensagem.png',
    },
    'reclamacao': {
        'username': 'ML Reclamação',
        'role': '<@&1398489141326385193>',
        'color': 0xfc0303,
        'avatar_url': _URLBASE_AVATARS + 'reclamacao.png',
    },
    'pergunta': {
        'username': 'ML Pergunta',
        'role': '<@&1398489238231846954>',
        'color': 0x8b07f0,
        'avatar_url': _URLBASE_AVATARS + 'pergunta.png',
    },
    'debug': {
        'username': 'ML Debug',
        'role': '<@&1398701101963804672>',
        'color': 0xfcf803,
        'avatar_url': _URLBASE_AVATARS + 'debug.png',
    },
}

EMOJI_SHIP = {
        'drop_off': '<:drop_off:1501601374482468895>',
        'xd_drop_off': '<:xd_drop_off:1501601059271868578>',
        'self_service': '<:self_service:1501600732405567659>',
        'fulfillment': '<:fulfillment:1501596852267778079>',
    }

POST_PURCHASE_DICT = {
        'mediations': 'Reclamação entre comprador e vendedor.',
        'return': 'Devolução do produto.',
        'fulfillment': 'Reclamação entre comprador e Mercado Livre com origem de compra com envio full.',
        'ml_case': 'Cancelamento da compra por parte do comprador devido a envio demorado.',
        'cancel_sale': 'Cancelamento da compra por parte do vendedor.',
        'cancel_purchase':'Cancelamento da compra por parte do comprador.',
        'change': 'Troca do produto.',
    }