"""Reenvia notificações reais da tabela posts para uma instância (ensaio).

Uso (dentro do container):
    python -m scripts.replay --url http://127.0.0.1:8000/ --per-topic 3
"""
import argparse
import ast
import json

import requests

from app import db, log

_logger = log.get('replay')


def parse(content):
    try:
        return json.loads(content)
    except ValueError:
        return ast.literal_eval(content)  # registros antigos gravados com str(dict)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000/')
    parser.add_argument('--per-topic', type=int, default=3)
    parser.add_argument('--topics', default='orders_v2,messages,questions,post_purchase')
    args = parser.parse_args()
    log.setup('replay')

    for topic in args.topics.split(','):
        rows = db.fetch(
            'SELECT MAX(id) id, resource FROM posts WHERE topic = %s GROUP BY resource ORDER BY id DESC LIMIT %s',
            (topic, args.per_topic),
        )
        for r in rows:
            content = db.fetch('SELECT content FROM posts WHERE id = %s', (r['id'],))[0]['content']
            data = parse(content)
            resp = requests.post(args.url, json=data, timeout=10)
            _logger.info(f'{topic} {data.get("resource")}: {resp.status_code} {resp.text.strip()}')


if __name__ == '__main__':
    main()
