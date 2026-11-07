"""Fila de notificações no MySQL (tabela webhook_queue)."""
import json
import uuid

from app import config, db

T = config.QUEUE_TABLE  # nome validado em config (só \w)
DONE_STATES = "('done','skipped','failed')"

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS `{T}` (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  dedup_key VARCHAR(191) NOT NULL,
  topic VARCHAR(50) NOT NULL,
  handler VARCHAR(30) NOT NULL,
  payload JSON NULL,
  is_debug TINYINT(1) NOT NULL DEFAULT 0,
  status ENUM('pending','processing','done','skipped','failed') NOT NULL DEFAULT 'pending',
  dirty TINYINT(1) NOT NULL DEFAULT 0,
  attempts INT NOT NULL DEFAULT 0,
  next_attempt_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  alert_key VARCHAR(50) NULL,
  last_error TEXT NULL,
  note VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_dedup (dedup_key),
  KEY ix_due (status, next_attempt_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
"""


def create_table():
    db.execute(SCHEMA)


def dedup_key(data, handler, is_debug):
    if is_debug:
        return f"{data['resource']}#debug-{uuid.uuid4().hex[:8]}"
    if handler == 'debug':
        return f"debug:{data.get('_id') or uuid.uuid4().hex}"
    return str(data['resource'])


def enqueue(data, handler, is_debug=False, recheck=False):
    """Grava a notificação. Devolve 'new', 'recheck' ou 'duplicate'.

    Recursos com recheck (reclamações) voltam para pending a cada notificação;
    se já estiverem em processamento, ficam marcados como dirty para reprocessar depois.
    """
    key = dedup_key(data, handler, is_debug)
    payload = json.dumps(data, ensure_ascii=False)
    if recheck:
        # colunas qualificadas: o alias "new" também tem status/payload e deixaria ambíguo
        s = f'`{T}`.status'
        update = f"""
          attempts = IF({s} IN {DONE_STATES}, 0, `{T}`.attempts),
          next_attempt_at = IF({s} IN {DONE_STATES}, NOW(), `{T}`.next_attempt_at),
          last_error = IF({s} IN {DONE_STATES}, NULL, `{T}`.last_error),
          dirty = IF({s} = 'processing', 1, `{T}`.dirty),
          payload = new.payload,
          status = IF({s} IN {DONE_STATES}, 'pending', {s})
        """
    else:
        update = 'id = id'
    rows = db.execute(
        f"""INSERT INTO `{T}` (dedup_key, topic, handler, payload, is_debug, status, next_attempt_at)
            VALUES (%s, %s, %s, %s, %s, 'pending', NOW()) AS new
            ON DUPLICATE KEY UPDATE {update}""",
        (key, data.get('topic', '-'), handler, payload, int(bool(is_debug))),
    )
    # MySQL: 1 = inserido, 2 = atualizado, 0 = nada mudou
    return {1: 'new', 2: 'recheck'}.get(rows, 'duplicate')


def recover_stuck():
    """Na partida do worker: jobs que ficaram em processing voltam para pending."""
    return db.execute(f"UPDATE `{T}` SET status = 'pending', dirty = 0 WHERE status = 'processing'")


def due(limit=20):
    return db.fetch(
        f"SELECT * FROM `{T}` WHERE status = 'pending' AND next_attempt_at <= NOW() ORDER BY id LIMIT %s",
        (limit,),
    )


def claim(job_id):
    return db.execute(
        f"UPDATE `{T}` SET status = 'processing', dirty = 0 WHERE id = %s AND status = 'pending'",
        (job_id,),
    ) == 1


def finish(job_id, status, alert_key=None, note=''):
    """Conclui o job. Se chegou notificação nova durante o processamento (dirty), volta para pending."""
    db.execute(
        f"""UPDATE `{T}` SET
              status = IF(dirty = 1, 'pending', %s),
              dirty = 0,
              attempts = 0,
              next_attempt_at = NOW(),
              alert_key = COALESCE(%s, alert_key),
              last_error = NULL,
              note = %s
            WHERE id = %s""",
        (status, alert_key, (note or '')[:255], job_id),
    )


def retry_later(job_id, attempts, delay_seconds, error):
    db.execute(
        f"""UPDATE `{T}` SET status = 'pending', attempts = %s,
              next_attempt_at = NOW() + INTERVAL %s SECOND, last_error = %s
            WHERE id = %s""",
        (attempts, int(delay_seconds), str(error)[:4000], job_id),
    )


def fail(job_id, attempts, error):
    db.execute(
        f"""UPDATE `{T}` SET status = IF(dirty = 1, 'pending', 'failed'), dirty = 0,
              attempts = %s, last_error = %s, next_attempt_at = NOW()
            WHERE id = %s""",
        (attempts, str(error)[:4000], job_id),
    )


def stats():
    return {r['status']: r['n'] for r in db.fetch(f'SELECT status, COUNT(*) n FROM `{T}` GROUP BY status')}
