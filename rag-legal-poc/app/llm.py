# app/llm.py
from __future__ import annotations
import json
import logging
import requests
from typing import Optional
from app import config

logger = logging.getLogger("rag.llm")

class ChatClient:
    def __init__(self):
        self.primary = {
            "name": "gpt4o-mini",
            "endpoint": config.GPT4O_ENDPOINT,
            "api_key": config.GPT4O_API_KEY,
            "model":   config.GPT4O_MODEL,
        }
        self.backup = {
            "name": "deepseek-v3",
            "endpoint": config.DEEPSEEK_ENDPOINT,
            "api_key": config.DEEPSEEK_API_KEY,
            "model":   config.DEEPSEEK_MODEL,
        }
        self.temperature = config.LLM_TEMPERATURE
        self.max_tokens = config.LLM_MAX_TOKENS
        self.timeout = config.LLM_TIMEOUT_SEC

    def _call(self, endpoint: str, api_key: str, model: str, system: str, user: str) -> Optional[str]:
        headers = {
            "Authorization": api_key,  # مقدار شما already شامل "apikey ..." است
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system or ""},
                {"role": "user", "content": user or ""},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=self.timeout)
        if resp.status_code != 200:
            logger.warning(f"[LLM] HTTP {resp.status_code} from {endpoint}: {resp.text[:300]}")
            return None
        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"[LLM] parse error from {endpoint}: {e} body={resp.text[:400]}")
            return None

    def chat(self, system: str, user: str) -> str:
        # Primary
        try:
            out = self._call(
                self.primary["endpoint"],
                self.primary["api_key"],
                self.primary["model"],
                system, user
            )
            if out:
                return out
        except Exception as e:
            logger.warning(f"[LLM] primary failed: {e}")

        # Backup
        try:
            out = self._call(
                self.backup["endpoint"],
                self.backup["api_key"],
                self.backup["model"],
                system, user
            )
            if out:
                return out
        except Exception as e:
            logger.warning(f"[LLM] backup failed: {e}")

        return "خطا در برقراری ارتباط با مدل زبانی. لطفاً بعداً دوباره تلاش کنید."
