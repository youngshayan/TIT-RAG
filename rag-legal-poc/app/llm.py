import requests
from app import config

class ChatClient:
    """
    اولویت: GPT-4o-mini (ArvanCloud)
    بکاپ: DeepSeek
    """

    def __init__(self):
        self.primary = {
            "endpoint": config.GPT4O_ENDPOINT,
            "api_key": config.GPT4O_API_KEY,
            "model": config.GPT4O_MODEL,
        }
        self.backup = {
            "endpoint": config.DEEPSEEK_ENDPOINT,
            "api_key": config.DEEPSEEK_API_KEY,
            "model": config.DEEPSEEK_MODEL,
        }

    def _call(self, settings, system: str, user: str) -> str:
        headers = {
            "Authorization": settings["api_key"],
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        r = requests.post(settings["endpoint"], headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

    def chat(self, system: str, user: str) -> str:
        try:
            return self._call(self.primary, system, user)
        except Exception as e:
            print("⚠️ GPT-4o-mini failed, switching to DeepSeek:", e)
            return self._call(self.backup, system, user)
