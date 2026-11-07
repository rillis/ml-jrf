#!/usr/bin/env bash
# Sobe o worker e o gunicorn; se qualquer um morrer, o container sai e o Docker reinicia.
set -u
python -m app.worker &
WORKER=$!
gunicorn -c gunicorn.conf.py 'app.web:create_app()' &
WEB=$!
trap 'kill -TERM $WORKER $WEB 2>/dev/null' TERM INT
wait -n
code=$?
kill -TERM $WORKER $WEB 2>/dev/null
wait
exit $code
