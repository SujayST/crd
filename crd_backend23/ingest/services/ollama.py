import requests
from django.conf import settings


class OllamaClient:
    def __init__(self, base_url=None, model=None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.OLLAMA_MODEL

    def generate(self, prompt: str, options=None, timeout=600):
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if options:
            payload["options"] = options
        resp = requests.post(self.base_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["response"].strip()
