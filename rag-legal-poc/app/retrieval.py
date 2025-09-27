# app/retrieval.py
from __future__ import annotations
from typing import Dict, List, Tuple, Any
from app.llm import ChatClient
from app.store import Store
from app import config

# ریرنکر را تنبل بسازیم و قابل خاموش/روشن
_RERANKER = None  # type: ignore

def _get_reranker():
    """Create CrossEncoder lazily (only if enabled)."""
    global _RERANKER
    if not getattr(config, "USE_RERANKER", False):
        return None
    if _RERANKER is None:
        from sentence_transformers import CrossEncoder
        _RERANKER = CrossEncoder(config.RERANKER_MODEL, max_length=512)
    return _RERANKER


RAG_SYSTEM = (
    "تو یک دستیار حقوقی بانکی فارسی هستی. فقط بر اساس متون ارائه‌شده پاسخ بده. "
    "اگر پاسخ قطعی نیست یا مدرک کافی نیست صادقانه بگو «اطلاعی ندارم». "
    "در پایان پاسخ، منابع را با نام فایل و متادیتا ارائه کن. "
    + config.DISCLAIMER
)


def summarize_text(chatter: ChatClient, text: str, extracted_meta: Dict[str, Any]) -> str:
    sys = "خلاصه‌ساز حقوقی فارسی. نکات کلیدی، دامنه اجرا، استثناها و مواد مهم را فهرست‌وار بده."
    meta_str = ""
    if extracted_meta:
        issuer = extracted_meta.get("issuer") or ""
        number = extracted_meta.get("number") or ""
        date = extracted_meta.get("issue_date") or extracted_meta.get("effective_date") or ""
        meta_str = f"\n\n[متادیتا: صادرکننده={issuer} | شماره={number} | تاریخ={date}]"

    # محدودیت طول برای کاهش هزینه و زمان
    max_chars = int(getattr(config, "SUMMARY_MAX_CHARS", 8000))
    safe_text = (text or "")[:max_chars]

    user = f"این متن را خلاصه کن، شفاف و دقیق:\n\n{safe_text}{meta_str}"
    return chatter.chat(system=sys, user=user)


def _rerank_pairs(query: str, candidates: List[Tuple[int, float, str]], store: Store, top_n: int) -> List[Tuple[int, float, str]]:
    if not candidates:
        return []
    reranker = _get_reranker()
    # اگر خاموش است، همان کاندیداهای اولیه را برمی‌گردانیم (سریع‌ترین حالت)
    if reranker is None:
        return candidates[:top_n]

    pairs, rows = [], []
    for cid, sc, tag in candidates:
        ch = store.get_chunk(cid)
        if not ch or not (ch.text or "").strip():
            continue
        pairs.append((query, ch.text))
        rows.append((cid, sc, tag))
    if not pairs:
        return []
    scores = reranker.predict(pairs).tolist()
    ranked = sorted(zip(rows, scores), key=lambda x: -x[1])[:top_n]
    return [(cid, float(orig_sc), tag) for ((cid, orig_sc, tag), _score) in ranked]


def _pick_segments_evenly(chunks: List[Any], limit: int) -> List[str]:
    """از بین لیست چانک‌های آپلودی (list[str] یا list[{'text': str}])، به‌شکل یکنواخت حداکثر limit سگمنت برمی‌داریم."""
    # نرمال‌سازی به لیست استرینگ
    clean = []
    for seg in chunks:
        txt = seg.get("text") if isinstance(seg, dict) else seg
        txt = (txt or "").strip()
        if txt:
            clean.append(txt)
    if not clean:
        return []

    if len(clean) <= limit:
        return clean

    # نمونه‌برداری یکنواخت (evenly spaced)
    step = max(1, len(clean) // limit)
    picked = [clean[i] for i in range(0, len(clean), step)]
    return picked[:limit]


def find_conflicts_against_index(
    store: Store,
    chatter: ChatClient,
    uploaded_chunks: List[Any],   # list[str] یا list[{"text": str}]
    uploaded_meta: Dict[str, Any],
    per_chunk_candidates: int = None,
    final_k: int = None
) -> List[Dict[str, Any]]:
    """
    1) از چانک‌های آپلودی فقط N سگمنت را انتخاب می‌کنیم (ANALYZE_MAX_SEGMENTS).
    2) برای هر سگمنت، Hybrid Search انجام می‌دهیم و (در صورت فعال بودن) ریرنک می‌کنیم.
    3) بهترین نتایج را ادغام/دی‌دوپ می‌کنیم و فقط K تای آن‌ها را برای قضاوت LLM نگه می‌داریم (CONFLICT_JUDGMENTS).
    """
    max_segments = int(getattr(config, "ANALYZE_MAX_SEGMENTS", 6))
    per_chunk_candidates = int(per_chunk_candidates or getattr(config, "PER_CHUNK_CANDIDATES", 2))
    final_k_conf = int(getattr(config, "CONFLICT_FINAL_K", 6))
    max_judgments = int(getattr(config, "CONFLICT_JUDGMENTS", 5))

    # 1) انتخاب سگمنت‌ها
    candidate_segments = _pick_segments_evenly(uploaded_chunks, max_segments)
    if not candidate_segments:
        return []

    # 2) جمع‌آوری کاندیدها
    collected: List[Tuple[int, float, str]] = []
    for seg_text in candidate_segments:
        hits = store.search_hybrid(seg_text, vec_k=config.VEC_K, bm25_k=config.BM25_K)
        hits = _rerank_pairs(seg_text, hits, store, per_chunk_candidates)
        collected.extend(hits)

    # 3) دی‌دوپ با نگهداشت بهترین امتیاز برای هر chunk_id
    best_map: Dict[int, Tuple[float, str]] = {}
    for cid, sc, tag in collected:
        if cid not in best_map or sc > best_map[cid][0]:
            best_map[cid] = (sc, tag)

    # 4) مرتب‌سازی کلی و محدود کردن تعداد
    top_all = sorted([(cid, sc, tag) for cid, (sc, tag) in best_map.items()],
                     key=lambda x: -x[1])[:final_k_conf]

    # 5) قضاوت LLM فقط برای تعداد محدود
    judge_sys = (
        "قاضی تعارض متون حقوقی. فقط بر اساس دو متن، مشخص کن تعارض (مغایرت) وجود دارد یا خیر. "
        "اگر تعارض هست، بند یا ماده متعارض را دقیق نشان بده و توضیح کوتاه بده."
    )

    # برای نمایش قطعه‌ای از آپلود (اولین سگمنت انتخابی)
    uploaded_piece = candidate_segments[0] if candidate_segments else ""

    out: List[Dict[str, Any]] = []
    for cid, score, tag in top_all[:max_judgments]:
        ch = store.get_chunk(cid)
        if not ch:
            continue
        doc = store.get_document(ch.doc_id)
        try:
            import json as _json
            doc_meta = (doc.meta and isinstance(doc.meta, str)) and _json.loads(doc.meta) or {}
        except Exception:
            doc_meta = {}

        user_prompt = (
            "متن اول (از سند آپلودی کاربر):\n"
            f"{uploaded_piece[:4000]}\n\n"
            "متن دوم (از پایگاه موجود):\n"
            f"{(ch.text or '')[:4000]}\n\n"
            "خروجی مطلوب:\n"
            "- تعارض: بله/خیر\n"
            "- توضیح کوتاه: چرا\n"
            "- اگر بله: اشاره دقیق به بخش‌های متعارض (کلمات/بندها)\n"
        )
        verdict = chatter.chat(system=judge_sys, user=user_prompt)

        out.append({
            "db_doc": {
                "doc_id": ch.doc_id,
                "title": (doc.title if doc else "") or "",
                "source_path": (doc.source_path if doc else "") or "",
                "meta": doc_meta
            },
            "db_chunk_id": ch.id,
            "score": round(float(score), 4),
            "source_tag": tag,
            "verdict": verdict,
            "snippets": {
                "uploaded": uploaded_piece[:600],
                "db": (ch.text or "")[:600]
            },
            "uploaded_meta": uploaded_meta or {}
        })

    return out
