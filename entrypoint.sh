#!/usr/bin/env bash
# Sobe o worker, o gunicorn e um vigia. Se qualquer um sair, o container sai e o Docker reinicia.
# O vigia existe porque o Docker não reinicia container "unhealthy": um worker travado
# (vivo, mas sem processar) ficaria parado em silêncio.
set -u
HEARTBEAT="${HEARTBEAT_FILE:-/tmp/ml-jrf-worker.heartbeat}"
MAX_AGE="${WATCHDOG_MAX_AGE:-600}"
STARTED=$(date +%s)

watchdog() {
    while sleep 30; do
        now=$(date +%s)
        last=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo "$STARTED")
        age=$(( now - last ))
        if [ "$age" -gt "$MAX_AGE" ]; then
            echo "[vigia] worker sem heartbeat há ${age}s (limite ${MAX_AGE}s): reiniciando o container" >&2
            exit 1
        fi
    done
}

python -m app.worker &
WORKER=$!
gunicorn -c gunicorn.conf.py 'app.web:create_app()' &
WEB=$!
watchdog &
WATCHDOG=$!
trap 'kill -TERM $WORKER $WEB $WATCHDOG 2>/dev/null' TERM INT
wait -n
code=$?
kill -TERM $WORKER $WEB $WATCHDOG 2>/dev/null
wait
exit $code
