from cfg import config

import requests, time, json
from pathlib import Path

TOKENS_FILE = Path(config.TOKENS_FILE_PATH)

def _get_tokens():
    if not TOKENS_FILE.exists():
        TOKENS_FILE.write_text(
            json.dumps({
                "token": "",
                "refresh_token": ""
            }),
            encoding="utf-8"
        )
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    
def get_token(token_type="token"):
    tokens = _get_tokens()
    return tokens.get(token_type, "")

def set_token(value, token_type="token"):
    tokens = _get_tokens()
    tokens[token_type] = str(value)

    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=4)

def do_refresh_token(app_id=config.APP_ID, SECRET_KEY=config.SECRET_KEY):
    refresh_token = get_token(token_type='refresh_token')

    url = config.ML_TOKEN_URL
    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "client_id": f"{app_id}",
        "client_secret": f"{SECRET_KEY}",
        "refresh_token": f"{refresh_token}",
    }
    response = requests.post(url, headers=headers, data=data, timeout=5)
    response.raise_for_status()

    js = response.json()
    set_token(js['access_token'])
    set_token(js['refresh_token'], token_type='refresh_token')
    if config.DEBUG: print(f'Token refreshed, new token ({js["access_token"]}) new refresh_token ({js["refresh_token"]})')

def get(url, params=None, max_tries=3):
    tries = 0
    while True:
        headers = {
            "Authorization": "Bearer " + get_token()
        }
        
        if params is None:
            response = requests.get(url, headers=headers, timeout=5)
        else:
            response = requests.get(url, headers=headers, params=str(params), timeout=5)

        try:
            data = response.json()
        except ValueError:
            data = response.text

        if response.status_code < 400:
            if config.DEBUG: print(f'GET (ML) com sucesso! ({url})')
            return data
        else:
            if tries > max_tries:
                print("Limite de erro excedido, retornando None.")
                print(f'{response.status_code} - {response.reason}')
                return None
            
            print(f"Erro no GET, tentando novamente ({tries+1}/{max_tries})")
            print(f'{response.status_code} - {response.reason}')

            if tries == 0: #tenta resetar o token se for a primeira tentativa
                do_refresh_token()

            tries += 1
            time.sleep(1)