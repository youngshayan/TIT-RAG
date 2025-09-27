# app/retrieval.py
from __future__ import annotations
from typing import Dict, List, Tuple, Any
from sentence_transformers import CrossEncoder

from app.llm import ChatClient
from app.store import Store
from app import config

RAG_SYSTEM = (
    "تو یک دستیار حقوقی بانکی فارسی هستی. فقط بر اساس متون ارائه‌شده پاسخ بده. "
    "اگر پاسخ قطعی نیست یا مدرک کافی نیست صادقانه بگو «اطلاعی ندارم». "
    "در پایان پاسخ، منابع را با نام فایل و متادیتا ارائه کن. "
    + config.DISCLAIMER
)

_reranker = CrossEncoder(config.RERANKER_MODEL, max_length=512)


def summarize_text(chatter: ChatClient, text: str, extracted_meta: Dict[str, Any]) -> str:
    sys = "خلاصه‌ساز حقوقی فارسی. نکات کلیدی، دامنه اجرا، استثناها و مواد مهم را فهرست‌وار بده."
    meta_str = ""
    if extracted_meta:
        issuer = extracted_meta.get("issuer") or ""
        number = extracted_meta.get("number") or ""
        date = extracted_meta.get("issue_date") or extracted_meta.get("effective_date") or ""
        meta_str = f"\n\n[متادیتا: صادرکننده={issuer} | شماره={number} | تاریخ={date}]"
    user = f"این متن را خلاصه کن، شفاف و دقیق:\n\n{text[:18000]}{meta_str}"
    return chatter.chat(system=sys, user=user)


def _rerank_pairs(query: str, candidates: List[Tuple[int, float, str]], store: Store, top_n: int) -> List[Tuple[int, float, str]]:
    pairs, rows = [], []
    for cid, sc, tag in candidates:
        ch = store.get_chunk(cid)
        if not ch:
            continue
        pairs.append((query, ch.text))
        rows.append((cid, sc, tag))
    if not pairs:
        return []
    scores = _reranker.predict(pairs).tolist()
    ranked = sorted(zip(rows, scores), key=lambda x: -x[1])[:top_n]
    return [(cid, float(orig_sc), tag) for ((cid, orig_sc, tag), _score) in ranked]


def find_conflicts_against_index(
    store: Store,
    chatter: ChatClient,
    uploaded_chunks: List[Any],  # می‌تواند list[str] یا list[{"text": str}] باشد
    uploaded_meta: Dict[str, Any],
    per_chunk_candidates: int = 3,
    final_k: int = 15
) -> List[Dict[str, Any]]:
    """
    برای هر چانک از سند آپلودی، نتایج نزدیک از ایندکس موجود را می‌گیریم (Hybrid+Rerank)
    سپس با کمک LLM، تعارض/عدم تعارض را تشخیص می‌دهیم و خروجی به‌صورت انسانی (نام فایل+متادیتا) برمی‌گردد.
    """
    # 1) جمع‌آوری کاندیدها (فیکس: اگر uploaded_chunks آیتم‌های دیکشنری دارد، متن را از کلید 'text' بگیر)
    candidates: List[Tuple[int, float, str]] = []
    clean_uploaded: List[str] = []
    for seg in uploaded_chunks:
        seg_text = seg.get("text") if isinstance(seg, dict) else seg
        seg_text = seg_text or ""
        clean_uploaded.append(seg_text)
        hits = store.search_hybrid(seg_text, vec_k=config.VEC_K, bm25_k=config.BM25_K)
        hits = _rerank_pairs(seg_text, hits, store, per_chunk_candidates)
        candidates.extend(hits)

    # dedupe by chunk_id, keep best score
    best_map: Dict[int, Tuple[float, str]] = {}
    for cid, sc, tag in candidates:
        if cid not in best_map or sc > best_map[cid][0]:
            best_map[cid] = (sc, tag)
    # sort and keep top-N globally
    top = sorted([(cid, sc, tag) for cid, (sc, tag) in best_map.items()], key=lambda x: -x[1])[:final_k]

    # 2) LLM قضاوت روی هر زوج (uploaded_seg vs db_chunk)
    out: List[Dict[str, Any]] = []
    judge_sys = (
        "قاضی تعارض متون حقوقی. فقط بر اساس دو متن، مشخص کن تعارض (مغایرت) وجود دارد یا خیر. "
        "اگر تعارض هست، بند یا ماده متعارض را دقیق نشان بده و توضیح کوتاه بده."
    )

    # انتخاب یک قطعه‌ی نزدیک از آپلود برای نمایش (می‌توان بهبود داد: نزدیک‌ترین با امبدینگ)
    uploaded_piece = clean_uploaded[0] if clean_uploaded else ""

    for cid, score, tag in top:
        ch = store.get_chunk(cid)
        if not ch:
            continue
        doc = store.get_document(ch.doc_id)

        try:
            doc_meta = (doc.meta and isinstance(doc.meta, str)) and __import__("json").loads(doc.meta) or {}
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
