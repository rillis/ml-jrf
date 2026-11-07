FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --uid 1000 --create-home app \
    && mkdir -p /app/data /app/logs \
    && chown app:app /app/data /app/logs

COPY app ./app
COPY scripts ./scripts
COPY gunicorn.conf.py entrypoint.sh ./

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

CMD ["bash", "entrypoint.sh"]
