"""Logs coloridos no stdout e security.log rotativo."""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from zoneinfo import ZoneInfo

from app import config

RESET = '\033[0m'
DIM = '\033[2m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[95m'

_LEVEL_COLORS = {
    logging.DEBUG: DIM,
    logging.WARNING: YELLOW,
    logging.ERROR: RED,
    logging.CRITICAL: RED,
}

_TZ = ZoneInfo(config.TIMEZONE)


class ColorFormatter(logging.Formatter):
    def format(self, record):
        ts = datetime.fromtimestamp(record.created, _TZ).strftime('%Y-%m-%d %H:%M:%S')
        msg = record.getMessage()
        if record.exc_info:
            msg += '\n' + self.formatException(record.exc_info)
        color = getattr(record, 'color', None) or _LEVEL_COLORS.get(record.levelno, '')
        line = f'[{ts}] [{record.processName}] {msg}'
        return f'{color}{line}{RESET}' if color else line


class PlainFormatter(logging.Formatter):
    def format(self, record):
        ts = datetime.fromtimestamp(record.created, _TZ).strftime('%Y-%m-%d %H:%M:%S')
        return f'{ts} - {record.getMessage()}'


_configured = False


def setup(process_name=None):
    global _configured
    if _configured:
        return
    _configured = True
    if process_name:
        import multiprocessing
        multiprocessing.current_process().name = process_name

    app_logger = logging.getLogger('ml-jrf')
    app_logger.setLevel(config.LOG_LEVEL)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorFormatter())
    app_logger.addHandler(handler)
    app_logger.propagate = False

    sec = logging.getLogger('ml-jrf.security')
    sec.setLevel(logging.INFO)
    sec.propagate = False  # acesso vai só para o arquivo
    try:
        os.makedirs(config.LOG_DIR, exist_ok=True)
        fh = RotatingFileHandler(
            os.path.join(config.LOG_DIR, 'security.log'),
            maxBytes=config.SECURITY_LOG_MAX_BYTES,
            backupCount=config.SECURITY_LOG_BACKUPS,
            encoding='utf-8',
        )
        fh.setFormatter(PlainFormatter())
        sec.addHandler(fh)
    except OSError as err:  # sem permissão no volume: segue só com stdout
        app_logger.warning(f'security.log indisponível: {err}')


def get(name=''):
    return logging.getLogger('ml-jrf' + (f'.{name}' if name else ''))


def mask(secret):
    """Mostra só os 4 últimos caracteres de um token."""
    if not secret:
        return '<vazio>'
    return '…' + str(secret)[-4:]
