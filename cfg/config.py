from cfg import private

from datetime import datetime
from zoneinfo import ZoneInfo

def print_error(pre_msg, err):
    print(f'{RED}---------------------------[{datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")}]---------------------------{RESET}')
    print(f'{RED}ERRO!!!{RESET}')
    print(f'{RED}{pre_msg}{RESET}')
    print(f'{RED}{err}{RESET}')
    print(f'{RED}---------------------------------------------------------------------------{RESET}')


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
_URLBASE_AVATARS = 'https://dash.rillis.com.br/imgs/'

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
        'returns': 'Devolução do produto.',
        'fulfillment': 'Reclamação entre comprador e Mercado Livre com origem de compra com envio full.',
        'ml_case': 'Cancelamento da compra por parte do comprador devido a envio demorado.',
        'cancel_sale': 'Cancelamento da compra por parte do vendedor.',
        'cancel_purchase':'Cancelamento da compra por parte do comprador.',
        'change': 'Troca do produto.',
    }


#colors
# Reset
RESET = "\033[0m"

# Estilos
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
REVERSE = "\033[7m"
HIDDEN = "\033[8m"
STRIKETHROUGH = "\033[9m"

# Cores normais
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Cores brilhantes
BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Fundos
BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"
BG_MAGENTA = "\033[45m"
BG_CYAN = "\033[46m"
BG_WHITE = "\033[47m"

# Fundos brilhantes
BG_BRIGHT_BLACK = "\033[100m"
BG_BRIGHT_RED = "\033[101m"
BG_BRIGHT_GREEN = "\033[102m"
BG_BRIGHT_YELLOW = "\033[103m"
BG_BRIGHT_BLUE = "\033[104m"
BG_BRIGHT_MAGENTA = "\033[105m"
BG_BRIGHT_CYAN = "\033[106m"
BG_BRIGHT_WHITE = "\033[107m"