from cfg import config
import requests

class DiscordWebhook:
    def __init__(self, webhook_url=None, debug_url=False):
        self.webhook_url = webhook_url or (config.WEBHOOK_URL if not debug_url else config.WEBHOOK_URL_DEBUG)
        self.session = requests.Session()
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def send(self, data):
        if data is None:
            return None
        
        if not self.session:
            raise Exception("Webhook fechado.")
        response = self.session.post(self.webhook_url, json=data, timeout=10)
        response.raise_for_status()
        if config.DEBUG: print(f'Discord: Mensagem enviada com sucesso. ({data["username"]})')
        return response

    def close(self):
        if self.session:
            self.session.close()
            self.session = None
    
