"""Reautoriza o app do ML quando o refresh token for recusado.

1. Abra a URL de autorização (python -m scripts.authorize --url) logado na conta da loja
2. Copie o code= da URL para onde o ML redirecionar
3. python -m scripts.authorize --code <code> --redirect-uri <mesma URI do app>

O worker percebe sozinho na próxima tentativa (até 5 min) e retoma a fila.
"""
import argparse

from app import config, log
from app.handlers.debug import authorize_url
from app.ml import MLClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', action='store_true', help='só mostra a URL de autorização')
    parser.add_argument('--code')
    parser.add_argument('--redirect-uri', default=config.ML_REDIRECT_URI)
    args = parser.parse_args()
    log.setup('authorize')
    logger = log.get('authorize')

    if args.url or not args.code:
        print(authorize_url() if not args.redirect_uri else authorize_url().replace('<redirect_uri do app>', args.redirect_uri))
        return
    if not args.redirect_uri:
        parser.error('--redirect-uri é obrigatório (ou defina ML_REDIRECT_URI no .env)')

    ml = MLClient()
    js = ml.authorize(args.code, args.redirect_uri)
    logger.info(f'Tokens novos gravados (token {log.mask(js["access_token"])}, refresh {log.mask(js["refresh_token"])})')
    me = ml.get('/users/me')
    logger.info(f'Conta autorizada: {me.get("nickname")}')


if __name__ == '__main__':
    main()
