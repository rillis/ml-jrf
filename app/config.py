"""Configuração lida do ambiente (.env) e constantes dos alertas."""
import os
import re


def _env(name, default=None, cast=str, required=False):
    value = os.environ.get(name, default)
    if required and (value is None or value == ''):
        raise RuntimeError(f'Variável de ambiente obrigatória ausente: {name}')
    if value is None or value == '':
        return value
    return cast(value)


def _bool(value):
    return str(value).strip().lower() in ('1', 'true', 'yes', 'sim', 'on')


# Logs
LOG_LEVEL = _env('LOG_LEVEL', 'INFO').upper()
LOG_DIR = _env('LOG_DIR', 'logs')
SECURITY_LOG_MAX_BYTES = _env('SECURITY_LOG_MAX_BYTES', 5 * 1024 * 1024, int)
SECURITY_LOG_BACKUPS = _env('SECURITY_LOG_BACKUPS', 3, int)

# Ensaio: usa outra tabela de fila, não grava histórico nem posts e não menciona cargos
ENSAIO = _bool(_env('ENSAIO', '0'))

# Mercado Livre
APP_ID = _env('ML_APP_ID', 0, int)
SECRET_KEY = _env('ML_SECRET_KEY', '')
SELLER_ID = _env('ML_SELLER_ID', 0, int)
CONTA = _env('ML_CONTA', '')
ML_API_URL = 'https://api.mercadolibre.com'
ML_TOKEN_URL = 'https://api.mercadolibre.com/oauth/token'
TOKENS_FILE = _env('TOKENS_FILE', 'data/tokens.json')

# MySQL
DB_HOST = _env('DB_HOST', '127.0.0.1')
DB_PORT = _env('DB_PORT', 3306, int)
DB_USER = _env('DB_USER', '')
DB_PASSWORD = _env('DB_PASSWORD', '')
DB_DATABASE = _env('DB_DATABASE', '')
DB_POOL_SIZE = _env('DB_POOL_SIZE', 5, int)
QUEUE_TABLE = _env('QUEUE_TABLE', 'webhook_queue_ensaio' if ENSAIO else 'webhook_queue')
if not re.fullmatch(r'\w+', QUEUE_TABLE):
    raise RuntimeError(f'QUEUE_TABLE inválido: {QUEUE_TABLE!r}')

# Discord
WEBHOOK_URL = _env('DISCORD_WEBHOOK_URL', '')
WEBHOOK_URL_DEBUG = _env('DISCORD_WEBHOOK_URL_DEBUG', '')

# Worker
WORKER_POLL_SECONDS = _env('WORKER_POLL_SECONDS', 2, float)
RETRY_BACKOFF = [30, 120, 600, 1800, 3600]  # segundos de espera após a 1ª..5ª falha
HEARTBEAT_FILE = _env('HEARTBEAT_FILE', '/tmp/ml-jrf-worker.heartbeat')
HEARTBEAT_MAX_AGE = 300  # /health fica unhealthy (um job lento com a API do ML instável leva minutos)
# O vigia do entrypoint.sh reinicia o container com heartbeat mais velho que WATCHDOG_MAX_AGE (padrão 600s)
TOKEN_PAUSE_SECONDS = 300  # com token inválido, a fila pausa e testa de novo a cada 5 min
TOKEN_INVALID_FILE = _env('TOKEN_INVALID_FILE', '/tmp/ml-jrf-token-invalid')
ML_REDIRECT_URI = _env('ML_REDIRECT_URI', '')
PING_CACHE_SECONDS = _env('PING_CACHE_SECONDS', 10, float)  # /token/ping reaproveita o resultado por esse tempo
LATE_NOTICE_HOURS = 24
TIMEZONE = 'America/Sao_Paulo'

# Avatares e cargos dos alertas
_URLBASE_AVATARS = 'https://dash.rillis.com.br/imgs/'

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
    'cancel_purchase': 'Cancelamento da compra por parte do comprador.',
    'change': 'Troca do produto.',
}
