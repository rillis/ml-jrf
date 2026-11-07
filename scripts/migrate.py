"""Cria a tabela da fila e importa o histórico já alertado como "done".

Uso (dentro do container):
    python -m scripts.migrate                      # só cria a tabela
    python -m scripts.migrate --import-recent logs/recent.log --import-history
"""
import argparse
import ast
from collections import defaultdict

from app import config, db, log
from app import queue

_logger = log.get('migrate')

INSERT = (f"INSERT IGNORE INTO `{config.QUEUE_TABLE}` (dedup_key, topic, handler, status, alert_key, note) "
          "VALUES (%s, %s, %s, 'done', %s, %s)")


def keys_from_recent(path):
    """Converte as chaves do antigo logs/recent.log para (dedup_key, topic, handler, alert_key)."""
    with open(path, encoding='utf-8') as f:
        arr = ast.literal_eval(f.read())
    claims = defaultdict(int)
    rows = []
    for key in arr:
        if key.startswith('/post-purchase/'):
            base, _, n = key.rpartition('-')
            claims[base] = max(claims[base], int(n))
        elif key.startswith('/orders/'):
            rows.append((key, 'orders_v2', 'orders_v2', None))
        elif key.startswith('/questions/'):
            rows.append((key, 'questions', 'questions', None))
        else:
            rows.append((key, 'messages', 'messages', None))
    rows += [(base, 'post_purchase', 'claims', str(n)) for base, n in claims.items()]
    return rows


def keys_from_history():
    rows = [(r['res_id'], 'orders_v2', 'orders_v2', None)
            for r in db.fetch("SELECT DISTINCT res_id FROM orders_v2 WHERE res_id LIKE '/orders/%'")]
    rows += [(r['res_id'], 'questions', 'questions', None)
             for r in db.fetch("SELECT DISTINCT res_id FROM questions WHERE res_id LIKE '/questions/%'")]
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--import-recent', metavar='ARQUIVO')
    parser.add_argument('--import-history', action='store_true', help='importa res_id de orders_v2 e questions')
    args = parser.parse_args()
    log.setup('migrate')

    queue.create_table()
    _logger.info(f'Tabela {config.QUEUE_TABLE} pronta')

    rows = []
    if args.import_recent:
        rows += [r + ('importado do recent.log',) for r in keys_from_recent(args.import_recent)]
    if args.import_history:
        rows += [r + ('importado do histórico',) for r in keys_from_history()]
    inserted = 0
    for dedup_key, topic, handler, alert_key, note in rows:
        inserted += db.execute(INSERT, (dedup_key, topic, handler, alert_key, note))
    if rows:
        _logger.info(f'{len(rows)} chaves lidas, {inserted} novas importadas como done')
    _logger.info(f'Fila: {queue.stats()}')


if __name__ == '__main__':
    main()
