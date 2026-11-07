"""Envio para webhooks do Discord respeitando os limites da API."""
import copy

import requests

from app import config, log

_logger = log.get('discord')

LIMIT_CONTENT = 2000
LIMIT_TITLE = 256
LIMIT_DESCRIPTION = 4096
LIMIT_FIELD_NAME = 256
LIMIT_FIELD_VALUE = 1024
LIMIT_AUTHOR_NAME = 256
LIMIT_FIELDS = 25
LIMIT_EMBEDS = 10
EMPTY_TEXT = '(sem texto)'


def truncate(text, limit):
    text = '' if text is None else str(text)
    return text if len(text) <= limit else text[:limit - 3] + '...'


def sanitize(payload):
    """Cópia do payload ajustada aos limites do Discord."""
    p = copy.deepcopy(payload)
    if 'content' in p:
        p['content'] = truncate(p['content'], LIMIT_CONTENT)
    embeds = p.get('embeds') or []
    p['embeds'] = embeds[:LIMIT_EMBEDS]
    for emb in p['embeds']:
        if 'title' in emb:
            emb['title'] = truncate(emb['title'], LIMIT_TITLE) or EMPTY_TEXT
        if 'description' in emb:
            if emb['description']:
                emb['description'] = truncate(emb['description'], LIMIT_DESCRIPTION)
            else:
                del emb['description']
        if 'author' in emb and 'name' in emb['author']:
            emb['author']['name'] = truncate(emb['author']['name'], LIMIT_AUTHOR_NAME)
        fields = (emb.get('fields') or [])[:LIMIT_FIELDS]
        for f in fields:
            f['name'] = truncate(f.get('name'), LIMIT_FIELD_NAME) or '-'
            value = f.get('value')
            f['value'] = truncate(value, LIMIT_FIELD_VALUE) if value not in (None, '') and str(value).strip() else EMPTY_TEXT
        emb['fields'] = fields
    if config.ENSAIO:
        p['allowed_mentions'] = {'parse': []}  # ensaio não menciona ninguém
    return p


class DiscordSender:
    def __init__(self, url=None, debug_url=None, session=None):
        self.urls = {
            'main': url if url is not None else config.WEBHOOK_URL,
            'debug': debug_url if debug_url is not None else config.WEBHOOK_URL_DEBUG,
        }
        self.session = session or requests.Session()

    def send(self, payload, channel='main'):
        url = self.urls[channel]
        if not url:
            raise RuntimeError(f'Webhook do Discord ({channel}) não configurado')
        resp = self.session.post(url, json=sanitize(payload), timeout=10)
        if resp.status_code >= 400:
            raise RuntimeError(f'Discord {resp.status_code}: {resp.text[:300]}')
        _logger.debug(f'Discord: enviado ({payload.get("username")}, canal {channel})')
        return resp
