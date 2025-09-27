# app/llm.py
from __future__ import annotations
import json
import logging
import time
from typing import Optional

import requests

from app import config

logger = logging.getLogger("rag.llm")


def _try_decode_json(resp: requests.Response) -> Optional[dict]:
    """
    تلاش برای برگرداندن JSON حتی اگر سرور خروجی را فشرده کرده باشد ولی هدر درست نداده باشد.
    """
    # 1) راه ساده
    try:
        return resp.json()
    except Exception:
        pass

    raw = resp.content or b""
    if not raw:
        return None

    # 2) اگر هدر Content-Encoding داده بود، بر اساس آن عمل کن
    enc = (resp.headers.get("Content-Encoding") or "").lower().strip()
    # در هر صورت چند مسیر را امتحان می‌کنیم:
    cand_bytes = [raw]

    # اگر گفته br/gzip/deflate …
    try:
        if enc == "gzip":
            import gzip
            cand_bytes.insert(0, gzip.decompress(raw))
        elif enc == "br":
            import brotli
            cand_bytes.insert(0, brotli.decompress(raw))
        elif enc in ("deflate",):
            import zlib
            cand_bytes.insert(0, zlib.decompress(raw))
    except Exception:
        pass

    # 3) حتی اگر هدر نبود، حدس می‌زنیم شاید gzip یا br باشد
    try:
        import gzip
        cand_bytes.insert(0, gzip.decompress(raw))
    except Exception:
        pass
    try:
        import brotli
        cand_bytes.insert(0, brotli.decompress(raw))
    except Exception:
        pass
    try:
        import zlib
        cand_bytes.insert(0, zlib.decompress(raw))
    except Exception:
        pass

    # 4) هر گزینه را امتحان کن تا JSON شود
    for b in cand_bytes:
        try:
            return json.loads(b.decode("utf-8", errors="ignore"))
        except Exception:
            continue

    return None


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
        self.timeout = config.LLM_TIMEOUT_SEC  # پیشنهاد: 12-15s اگر شبکه ناپایدار است
        self.retries = 2

        # هدرها: درخواست JSON خالص (بدون فشرده‌سازی)
        self.base_headers = {
            "Authorization": "",  # در هر فراخوانی ست می‌کنیم
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "identity",  # <-- مهم
            "Connection": "keep-alive",
        }

    def _call_once(self, endpoint: str, api_key: str, model: str, system: str, user: str) -> Optional[str]:
        headers = dict(self.base_headers)
        headers["Authorization"] = api_key  # شما قبلاً "apikey ..." گذاشته‌ای

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
        t0 = time.time()
        resp = requests.post(endpoint, headers=headers, data=json.dumps(payload), timeout=self.timeout)
        dt = (time.time() - t0) * 1000.0

        if resp.status_code != 200:
            # اگر 200 نبود، لاگ کوتاه
            txt = resp.text
            try:
                txt = txt[:300]
            except Exception:
                pass
            logger.warning(f"[LLM] HTTP {resp.status_code} from {endpoint} in {dt:.1f}ms: {txt}")
            return None

        # تلاش برای JSON مطمئن
        data = _try_decode_json(resp)
        if not data:
            logger.warning(f"[LLM] parse error from {endpoint}: status=200 but body not JSON (len={len(resp.content)})")
            return None

        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"[LLM] JSON shape error from {endpoint}: {e}")
            return None

    def _call(self, endpoint: str, api_key: str, model: str, system: str, user: str) -> Optional[str]:
        # چند تلاش سبک برای transient خطاها
        last_err = None
        for attempt in range(1, self.retries + 1):
            try:
                out = self._call_once(endpoint, api_key, model, system, user)
                if out:
                    return out
            except requests.Timeout as e:
                last_err = e
                logger.warning(f"[LLM] timeout (attempt {attempt}) on {endpoint}")
            except requests.RequestException as e:
                last_err = e
                logger.warning(f"[LLM] request error (attempt {attempt}) on {endpoint}: {e}")
            except Exception as e:
                last_err = e
                logger.warning(f"[LLM] unexpected error (attempt {attempt}) on {endpoint}: {e}")
        if last_err:
            logger.warning(f"[LLM] giving up on {endpoint}: last_error={last_err}")
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
