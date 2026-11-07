import json

from app import config
from app.handlers import Outcome


def payload_for(title, content, method='POST'):
    info = config.INFOS['debug']
    return {
        'username': info['username'],
        'avatar_url': info['avatar_url'],
        'content': f"{info['role']} **{method} recebido!**",
        'embeds': [{'title': title, 'description': content, 'color': info['color']}],
    }


def handle(data, job, ml=None, now=None):
    """Notificação sem handler: manda o conteúdo bruto para o canal de debug."""
    body = json.dumps(data, ensure_ascii=False, indent=1)
    return Outcome(payload=payload_for('Conteúdo da Requisição:', body), channel='debug', note='sem handler')


def failure_payload(job, error):
    info = config.INFOS['debug']
    return {
        'username': info['username'],
        'avatar_url': info['avatar_url'],
        'content': f"{info['role']} **Notificação falhou após todas as tentativas**",
        'embeds': [{
            'title': f"{job.get('topic')} — {job.get('dedup_key')}",
            'description': f'```{error}```',
            'color': info['color'],
            'fields': [{'name': 'Tentativas', 'value': str(job.get('attempts')), 'inline': True},
                       {'name': 'ID na fila', 'value': str(job.get('id')), 'inline': True}],
        }],
    }
