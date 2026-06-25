# app/conflict.py
from __future__ import annotations
from typing import Dict, List
from app.store import Store
from app.llm import ChatClient
from app import config
import json

if config.LANGUAGE == "en":
    CONFLICT_SYSTEM = (
        "You are a legal compliance analyst. Task: detect 'explicit conflict' or 'potential conflict' "
        "between new text and existing texts. Judge based only on the two texts. "
        "If no conflict, clearly say none. Output in JSON."
    )
    CONFLICT_USER_TMPL = """New text:
{new_text}

Existing text:
{old_text}

Output JSON with the following keys:
has_conflict: true/false
conflict_type: "explicit" | "potential" | "none"
evidence_new: short quote from new text (if conflict exists)
evidence_old: short quote from old text (if conflict exists)
explanation: brief and precise explanation
"""
else:
    CONFLICT_SYSTEM = (
        "تو یک تحلیلگر تطبیق حقوقی بانکی هستی. مأموریت: تشخیص «تعارض صریح» یا «تعارض محتمل» بین متن جدید و متون موجود. "
        "صرفاً بر اساس دو متن قضاوت کن. اگر تعارضی نیست، واضح بگو نیست. خروجی را JSON برگردان."
    )
    CONFLICT_USER_TMPL = """متن جدید:
{new_text}

متن موجود:
{old_text}

خروجی JSON با کلیدهای زیر بده:
has_conflict: true/false
conflict_type: "صریح" | "محتمل" | "ندارد"
evidence_new: نقل‌قول کوتاه از متن جدید (اگر تعارض هست)
evidence_old: نقل‌قول کوتاه از متن قدیم (اگر تعارض هست)
explanation: توضیح کوتاه و دقیق
"""

def conflict_check(store: Store, chatter: ChatClient, doc_id: int, per_chunk_candidates: int = 3, limit_chunks: int = 50) -> Dict:
    chunks_new = store.get_doc_chunks(doc_id)[:limit_chunks]
    results: List[Dict] = []

    for ch in chunks_new:
        hits = store.search(ch.text, top_k=per_chunk_candidates + 10)
        hits = [(cid, s) for cid, s in hits if store.get_chunk(cid).doc_id != doc_id][:per_chunk_candidates]

        for cid, score in hits:
            old = store.get_chunk(cid)
            user_prompt = CONFLICT_USER_TMPL.format(new_text=ch.text, old_text=old.text)
            out = chatter.chat(system=CONFLICT_SYSTEM, user=user_prompt)
            payload = {}
            try:
                payload = json.loads(out)
            except Exception:
                payload = {"has_conflict": "parse_error", "raw": out[:1500]}

            results.append({
                "new_chunk_id": ch.id,
                "old_chunk_id": old.id,
                "old_doc_id": old.doc_id,
                "score": round(score, 4),
                "analysis": payload
            })
    return {"doc_id": doc_id, "results": results}