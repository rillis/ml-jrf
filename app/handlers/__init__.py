"""Registro de handlers por tópico do Mercado Livre."""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from app import config

TZ = ZoneInfo(config.TIMEZONE)


@dataclass
class Outcome:
    """Resultado de um handler.

    payload: mensagem para o Discord (None = nada a enviar, o job fica "skipped").
    channel: "main" ou "debug".
    history: função que grava o histórico depois do envio (falhas nela não reenviam o alerta).
    alert_key: estado lembrado para a próxima notificação do mesmo recurso (reclamações).
    note: motivo legível, gravado na fila.
    """
    payload: Optional[dict] = None
    channel: str = 'main'
    history: Optional[Callable[[], None]] = None
    alert_key: Optional[str] = None
    note: str = ''

    @classmethod
    def skip(cls, note, alert_key=None):
        return cls(payload=None, note=note, alert_key=alert_key)


def fmt_date(iso):
    """Data ISO do ML (qualquer fuso) no horário de São Paulo."""
    if not iso:
        return '-'
    dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ).strftime('%d/%m/%Y %H:%M')


def route(data):
    """Nome do handler para a notificação, ou None se o tópico é ignorado."""
    topic = data.get('topic')
    actions = data.get('actions') or []
    first = actions[0] if actions else None

    if topic in IGNORED_TOPICS:
        return None
    if topic == 'post_purchase':
        if first == 'claims_actions':
            return None
        if first == 'claims':
            return 'claims'
        return 'debug'
    return topic if topic in HANDLERS else 'debug'


IGNORED_TOPICS = {'items'}

# Handlers cuja deduplicação reavalia o recurso a cada notificação (em vez de alertar uma vez só)
RECHECK_HANDLERS = {'claims'}

from app.handlers import claims, debug, messages, orders, questions  # noqa: E402

HANDLERS = {
    'orders_v2': orders.handle,
    'messages': messages.handle,
    'questions': questions.handle,
    'claims': claims.handle,
    'debug': debug.handle,
}
