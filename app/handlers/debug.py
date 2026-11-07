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


def authorize_url():
    uri = config.ML_REDIRECT_URI or '<redirect_uri do app>'
    return (f'https://auth.mercadolivre.com.br/authorization?response_type=code'
            f'&client_id={config.APP_ID}&redirect_uri={uri}')


def token_invalid_payload(error):
    info = config.INFOS['debug']
    uri = config.ML_REDIRECT_URI or '<redirect_uri>'
    steps = (
        f'1. Abra (logado na conta {config.CONTA}): {authorize_url()}\n'
        '2. Copie o `code=` da URL para onde o ML redirecionar\n'
        f'3. No servidor: `docker exec ml-jrf python -m scripts.authorize --code <code> --redirect-uri {uri}`\n'
        'As notificações ficam guardadas na fila e saem sozinhas quando o token voltar.'
    )
    return {
        'username': info['username'],
        'avatar_url': info['avatar_url'],
        'content': f"{info['role']} **Token do Mercado Livre recusado: notificações pausadas**",
        'embeds': [{
            'title': 'Reautorize o app do ML',
            'description': f'{steps}\n\n```{error}```',
            'color': 0xfc0303,
        }],
    }


def token_ok_payload(minutes):
    info = config.INFOS['debug']
    return {
        'username': info['username'],
        'avatar_url': info['avatar_url'],
        'content': f'**Token do Mercado Livre voltou a funcionar** após {minutes:.0f} min. A fila foi retomada.',
    }


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
