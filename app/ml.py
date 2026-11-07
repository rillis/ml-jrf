"""Cliente da API do Mercado Livre com renovação de token."""
import fcntl
import json
import os
import tempfile
import threading
import time
from pathlib import Path

import requests

from app import config, log

_logger = log.get('ml')


class MLError(Exception):
    def __init__(self, status, url, body=''):
        super().__init__(f'ML {status} em {url}: {str(body)[:300]}')
        self.status = status
        self.url = url


class MLNotFound(MLError):
    pass


class TokenInvalid(MLError):
    """O ML recusou o refresh token: só volta a funcionar reautorizando o app."""


class TokenStore:
    """tokens.json com trava entre processos e escrita atômica."""

    def __init__(self, path):
        self.path = Path(path)
        self._lock_path = self.path.with_suffix(self.path.suffix + '.lock')
        self._thread_lock = threading.Lock()

    def _locked(self):
        store = self

        class _Ctx:
            def __enter__(self):
                store._thread_lock.acquire()
                store.path.parent.mkdir(parents=True, exist_ok=True)
                self.fh = open(store._lock_path, 'a')
                fcntl.flock(self.fh, fcntl.LOCK_EX)
                return self

            def __exit__(self, *exc):
                fcntl.flock(self.fh, fcntl.LOCK_UN)
                self.fh.close()
                store._thread_lock.release()

        return _Ctx()

    def read(self):
        if not self.path.exists():
            return {'token': '', 'refresh_token': ''}
        with open(self.path, encoding='utf-8') as f:
            return json.load(f)

    def write(self, tokens):
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix='.tokens-', suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=4)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise


class MLClient:
    MAX_ATTEMPTS = 3

    def __init__(self, tokens_file=None, app_id=None, secret=None, session=None, sleep=time.sleep):
        self.tokens = TokenStore(tokens_file or config.TOKENS_FILE)
        self.app_id = app_id if app_id is not None else config.APP_ID
        self.secret = secret if secret is not None else config.SECRET_KEY
        self.session = session or requests.Session()
        self._sleep = sleep

    def _url(self, path):
        return path if path.startswith('http') else config.ML_API_URL + path

    def refresh_token(self, used_token=None):
        """Renova o token. Se outro processo já renovou (token mudou), não renova de novo."""
        with self.tokens._locked():
            current = self.tokens.read()
            if used_token is not None and current.get('token') != used_token:
                _logger.info('Token já renovado por outro processo, reaproveitando')
                return current['token']
            resp = self.session.post(
                config.ML_TOKEN_URL,
                headers={'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'refresh_token',
                    'client_id': str(self.app_id),
                    'client_secret': str(self.secret),
                    'refresh_token': current.get('refresh_token', ''),
                },
                timeout=10,
            )
            if resp.status_code in (400, 401, 403):  # invalid_grant: refresh token expirado ou revogado
                raise TokenInvalid(resp.status_code, config.ML_TOKEN_URL, resp.text)
            if resp.status_code >= 400:
                raise MLError(resp.status_code, config.ML_TOKEN_URL, resp.text)
            js = resp.json()
            current['token'] = js['access_token']
            current['refresh_token'] = js['refresh_token']
            self.tokens.write(current)
            _logger.info(f'Token renovado (token {log.mask(js["access_token"])}, refresh {log.mask(js["refresh_token"])})')
            return current['token']

    def get(self, path, params=None):
        url = self._url(path)
        refreshed = False
        attempt = 0
        while True:
            attempt += 1
            token = self.tokens.read().get('token', '')
            try:
                resp = self.session.get(url, headers={'Authorization': 'Bearer ' + token}, params=params, timeout=10)
            except requests.RequestException as err:
                if attempt >= self.MAX_ATTEMPTS:
                    raise MLError('rede', url, err) from err
                _logger.warning(f'GET {url} falhou ({err}), tentativa {attempt}/{self.MAX_ATTEMPTS}')
                self._sleep(attempt)
                continue

            status = resp.status_code
            if status < 400:
                _logger.debug(f'GET (ML) OK: {url}')
                try:
                    return resp.json()
                except ValueError:
                    return resp.text

            if status == 401 and not refreshed:
                _logger.warning(f'GET {url}: 401, renovando token')
                self.refresh_token(used_token=token)
                refreshed = True
                attempt -= 1  # a renovação não conta como tentativa
                continue

            if (status == 429 or status >= 500) and attempt < self.MAX_ATTEMPTS:
                wait = attempt * 2
                _logger.warning(f'GET {url}: {status}, nova tentativa em {wait}s ({attempt}/{self.MAX_ATTEMPTS})')
                self._sleep(wait)
                continue

            if status == 404:
                raise MLNotFound(status, url, resp.text)
            raise MLError(status, url, resp.text)

    def authorize(self, code, redirect_uri):
        """Troca o code da tela de autorização do ML por tokens novos."""
        with self.tokens._locked():
            resp = self.session.post(
                config.ML_TOKEN_URL,
                headers={'accept': 'application/json', 'content-type': 'application/x-www-form-urlencoded'},
                data={
                    'grant_type': 'authorization_code',
                    'client_id': str(self.app_id),
                    'client_secret': str(self.secret),
                    'code': code,
                    'redirect_uri': redirect_uri,
                },
                timeout=10,
            )
            if resp.status_code >= 400:
                raise MLError(resp.status_code, config.ML_TOKEN_URL, resp.text)
            js = resp.json()
            tokens = self.tokens.read()
            tokens['token'] = js['access_token']
            tokens['refresh_token'] = js['refresh_token']
            self.tokens.write(tokens)
            return js

    def get_or_none(self, path, params=None):
        """Para dados opcionais: 404 vira None em vez de exceção."""
        try:
            return self.get(path, params=params)
        except MLNotFound:
            return None
