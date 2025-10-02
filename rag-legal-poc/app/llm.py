# app/llm.py
from __future__ import annotations
import json
import logging
import time
from typing import Optional, Tuple

import requests

from app import config

logger = logging.getLogger("rag.llm")


def _try_decode_json(resp: requests.Response) -> Optional[dict]:

    try:
        return resp.json()
    except Exception:
        pass

    raw = resp.content or b""
    if not raw:
        return None

    enc = (resp.headers.get("Content-Encoding") or "").lower().strip()
    cand_bytes = [raw]

    try:
        if enc == "gzip":
            import gzip
            cand_bytes.insert(0, gzip.decompress(raw))
        elif enc == "br":
            import brotli
            cand_bytes.insert(0, brotli.decompress(raw))
        elif enc == "deflate":
            import zlib
            cand_bytes.insert(0, zlib.decompress(raw))
    except Exception:
        pass

    # حدسی
    for decomp in ("gzip", "br", "deflate"):
        try:
            if decomp == "gzip":
                import gzip
                cand_bytes.insert(0, gzip.decompress(raw))
            elif decomp == "br":
                import brotli
                cand_bytes.insert(0, brotli.decompress(raw))
            else:
                import zlib
                cand_bytes.insert(0, zlib.decompress(raw))
        except Exception:
            pass

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
        # Backup (AvalAI via OpenAI SDK)
        self.backup = {
            "name": "avalai",
            "endpoint": config.DEEPSEEK_ENDPOINT,
            "api_key": config.DEEPSEEK_API_KEY,
            "model":   config.DEEPSEEK_MODEL,
        }

        self.temperature = float(getattr(config, "LLM_TEMPERATURE", 0.2))
        self.max_tokens  = int(getattr(config, "LLM_MAX_TOKENS", 1200))

        # timeoutها
        self.default_timeout = float(getattr(config, "LLM_TIMEOUT_SEC", 40.0))
        self.primary_failover_timeout = float(getattr(config, "PRIMARY_TIMEOUT_FAILOVER_SEC", 10.0))

        self.base_headers = {
            "Authorization": "",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
        }

    # ---------- PRIMARY (requests) ----------
    def _post_json(
        self,
        endpoint: str,
        api_key: str,
        payload: dict,
        timeout_sec: float,
    ) -> Tuple[Optional[dict], Optional[str]]:
        headers = dict(self.base_headers)
        headers["Authorization"] = api_key

        t0 = time.time()
        try:
            resp = requests.post(
                endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=(min(5.0, timeout_sec), timeout_sec),
            )
        except requests.Timeout:
            dt = (time.time() - t0) * 1000.0
            return None, f"timeout_after_{timeout_sec:.1f}s ({dt:.0f}ms)"
        except requests.RequestException as e:
            dt = (time.time() - t0) * 1000.0
            return None, f"request_error ({dt:.0f}ms): {e}"

        dt = (time.time() - t0) * 1000.0
        if resp.status_code != 200:
            txt = ""
            try:
                txt = (resp.text or "")[:300]
            except Exception:
                pass
            return None, f"HTTP_{resp.status_code} ({dt:.0f}ms): {txt}"

        data = _try_decode_json(resp)
        if not data:
            return None, f"parse_error_200 ({dt:.0f}ms): body_len={len(resp.content)}"

        return data, None

    def _once_primary(self, system: str, user: str) -> Optional[str]:
        payload = {
            "model": self.primary["model"],
            "messages": [
                {"role": "system", "content": system or ""},
                {"role": "user", "content": user or ""},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        data, err = self._post_json(
            self.primary["endpoint"],
            self.primary["api_key"],
            payload,
            timeout_sec=self.primary_failover_timeout,  # fail-fast برای پرایمری
        )
        if err:
            logger.warning(f"[LLM] call failed on {self.primary['endpoint']}: {err}")
            return None

        try:
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"[LLM] JSON shape error from primary: {e}")
            return None

    # ---------- BACKUP (OpenAI SDK over AvalAI) ----------
    def _once_backup(self, system: str, user: str) -> Optional[str]:

        try:
            from openai import OpenAI
        except Exception as e:
            logger.warning(f"[LLM] openai SDK not installed: {e}")
            return None

        try:
            client = OpenAI(
                api_key=self.backup["api_key"],
                base_url=self.backup["endpoint"],
            )


            client = client.with_options(timeout=self.default_timeout)

            messages = [
                {"role": "system", "content": system or ""},
                {"role": "user", "content": user or ""},
            ]

            resp = client.chat.completions.create(
                model=self.backup["model"],
                messages=messages,
                max_tokens=min(self.max_tokens, 1500),
                temperature=self.temperature,
                top_p=0.9,
            )
            # parse
            try:
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"[LLM] backup JSON shape error: {e}")
                return None

        except Exception as e:
            logger.warning(f"[LLM] backup OpenAI call error: {e}")
            return None

    # ---------- Public ----------
    def chat(self, system: str, user: str) -> str:
        # 1) PRIMARY (failover 10s)
        try:
            out = self._once_primary(system, user)
            if out:
                return out
        except Exception as e:
            logger.warning(f"[LLM] primary exception: {e}")

        # 2) BACKUP (OpenAI SDK with AvalAI)
        try:
            out = self._once_backup(system, user)
            if out:
                return out
        except Exception as e:
            logger.warning(f"[LLM] backup exception: {e}")

        return "خطا در برقراری ارتباط با مدل زبانی. لطفاً دوباره تلاش کنید."
