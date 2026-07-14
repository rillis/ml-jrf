from cfg import config
from utils import ml
from handlers import main_handler

from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, request, abort
import logging, time, uuid

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, filename='security.log', format='%(asctime)s - %(message)s')
BAD_PATTERNS = ["androxgh0st", "<script>", "<?php", "union select", "1=1"]

@app.before_request
def block_suspicious_requests():
    if request.method == 'POST':
        if not request.form and not request.json and not request.data:
            logging.info(f"Bloqueado POST vazio de {request.remote_addr} - UA: {request.headers.get('User-Agent')}")
            abort(403)

    data_str = f"{request.form} {request.data} {request.json}".lower() if (request.form or request.data or request.json) else ""
    for pattern in BAD_PATTERNS:
        if pattern in data_str:
            logging.info(f"Bloqueado padrão '{pattern}' de {request.remote_addr} - Data: {data_str}")
            abort(403)

    ua = request.headers.get('User-Agent', '').lower()
    if 'curl' in ua or 'wget' in ua:
        logging.info(f"Bloqueado User-Agent suspeito: {ua} de {request.remote_addr}")


@app.route("/", methods=["POST"])
def home():
    if request.method == "POST":
        id = str(uuid.uuid4())[:8]
        if config.DEBUG: print(f'[{datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")}] POST [{id}] RECEBIDO -------------------')
        response = main_handler.handle(request)
        if config.DEBUG: print(f'Result: {response[1]} - {response[0]}')
        if config.DEBUG: print(f'[{datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")}] POST [{id}] FIM TRATAMENTO -------------')
        return response
    return {"status": "Wrong method"}, 405

if __name__ == "__main__":
    print('Waiting 5s to start') #Importante pois está com restart: unless-stopped
    time.sleep(5)

    print(f'Starting on {config.IP}:{config.PORT}')
    test_api = ml.get('https://api.mercadolibre.com/users/me', config.APP_ID)
    print(f'[{datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")}] OK! {test_api["nickname"]}. APP: {config.APP_ID}')

    app.run(host=config.IP, port=config.PORT, debug=config.DEBUG)