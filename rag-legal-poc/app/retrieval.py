# app/retrieval.py
from __future__ import annotations
from typing import Dict, List, Tuple, Any, Optional
import logging
import re
import json
import math

import requests

from app.llm import ChatClient
from app.store import Store
from app import config

logger = logging.getLogger("rag.retrieval")

# ----------------------------------------------------
# تنظیمات/پیش‌فرض‌ها
# ----------------------------------------------------
_AVALAI_API_KEY = getattr(config, "AVALAI_API_KEY", "")
_AVALAI_BASE_URL = getattr(config, "AVALAI_BASE_URL", "https://api.avalai.ir/v1")
_AVALAI_RERANK_MODEL = getattr(config, "AVALAI_RERANK_MODEL", "cohere.rerank-v3-5:0")
_USE_AVALAI_RERANK = bool(getattr(config, "USE_AVALAI_RERANK", True))

_LOCAL_HYBRID_CAND_K = int(getattr(config, "LOCAL_HYBRID_CAND_K", 60))
_LOCAL_HYBRID_TOP_K  = int(getattr(config, "LOCAL_HYBRID_TOP_K", 20))
_W_BM25 = float(getattr(config, "HYBRID_W_BM25", 0.6))
_W_TFIDF = float(getattr(config, "HYBRID_W_TFIDF", 0.4))

# ----------------------------------------------------
# وابستگی‌های اختیاری (برای Hybrid محلی)
# ----------------------------------------------------
_HAS_SKLEARN = True
_HAS_BM25 = True
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    _HAS_SKLEARN = False
    logger.warning("[RETR] scikit-learn در دسترس نیست؛ Hybrid محلی غیرفعال شد.")
try:
    from rank_bm25 import BM25Okapi
except Exception:
    _HAS_BM25 = False
    logger.warning("[RETR] rank-bm25 در دسترس نیست؛ Hybrid محلی غیرفعال شد.")


# ----------------------------------------------------
# UTILs
# ----------------------------------------------------
_FA_EN_TOKEN_RE = re.compile(r"[0-9A-Za-z\u0600-\u06FF]+", re.UNICODE)
_FA_EN_STOP = {
    "از","با","به","در","و","را","که","برای","یا","تا","این","آن","بین","بر","طبق","می","های",
    "خواهد","خواهند","کرد","شود","شده","بود","هست","نیست","است","هم","اما","بنابراین","اگر",
    "مثل","مانند","هر","هیچ","قبل","بعد","بدون","موضوع","تبصره","ماده","مواد","پیوست","صرفاً","حداکثر",
    "حداقل","اعم","تمامی","آنها","آن‌ها","ایشان","the","a","an","and","or","but","for","to","of",
    "in","on","at","by","from","with","as","is","are","was","were","be","been","being","this","that",
    "these","those","it","its","their","there","can","could","should","would","may","might","must",
    "shall","will","do","does","did"
}

def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    toks = [t.lower() for t in _FA_EN_TOKEN_RE.findall(text)]
    return [t for t in toks if t not in _FA_EN_STOP and len(t) >= 2]

def _preprocess_for_bm25(text: str) -> List[str]:
    return _tokenize(text or "")

def _normalize_scores(xs: List[float]) -> List[float]:
    if not xs:
        return []
    vmin, vmax = min(xs), max(xs)
    if math.isclose(vmin, vmax):
        return [1.0 for _ in xs]
    rng = (vmax - vmin) or 1.0
    return [(x - vmin) / rng for x in xs]


# ----------------------------------------------------
# AvalAI: Cohere Rerank
# ----------------------------------------------------
class AvalAIService:
    @staticmethod
    def rerank_documents(query: str, documents: List[str], top_k: int) -> List[int]:
        """
        ورودی: query و لیستی از متن اسناد (strings)
        خروجی: فهرست ایندکس‌های اسناد به ترتیب رِرَنک‌شده (0-based)
        """
        if not _USE_AVALAI_RERANK or not _AVALAI_API_KEY or not documents:
            return list(range(min(top_k, len(documents))))

        try:
            payload = {
                "model": _AVALAI_RERANK_MODEL,
                "query": query,
                "documents": documents,
                "top_n": min(top_k, len(documents))
            }
            headers = {
                "Authorization": f"Bearer {_AVALAI_API_KEY}",
                "Content-Type": "application/json"
            }
            url = f"{_AVALAI_BASE_URL}/rerank"
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"[AvalAI] rerank HTTP {resp.status_code}: {resp.text[:200]}")
                return list(range(min(top_k, len(documents))))
            data = resp.json()
            results = data.get("results") or []
            # هر result مثل {'index': i, 'relevance_score': ...}
            # ترتیب خروجی results بهینه است؛ همان ترتیب را برگردانیم
            order = [int(r.get("index", i)) for i, r in enumerate(results)]
            if not order:
                order = list(range(min(top_k, len(documents))))
            return order
        except Exception as e:
            logger.warning(f"[AvalAI] rerank error: {e}")
            return list(range(min(top_k, len(documents))))


# ----------------------------------------------------
# RAG System Prompt (بدون تغییر)
# ----------------------------------------------------
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

    max_chars = int(getattr(config, "SUMMARY_MAX_CHARS", 8000))
    safe_text = (text or "")[:max_chars]

    user = f"این متن را خلاصه کن، شفاف و دقیق:\n\n{safe_text}{meta_str}"
    return chatter.chat(system=sys, user=user)


# ----------------------------------------------------
# Hybrid محلی (روی کاندیدهای استور، نه کل کورپوس)
# ----------------------------------------------------
def _local_hybrid_rank(query: str, texts: List[str]) -> List[int]:
    """
    روی لیست کوچکی از متن‌ها (کاندیدهای اولیه از استور)، امتیاز Hybrid = 0.6*BM25 + 0.4*TFIDF
    برمی‌گرداند ترتیب ایندکس‌ها به‌صورت نزولی.
    اگر sklearn یا rank-bm25 نباشد، ترتیب اولیه حفظ می‌شود.
    """
    n = len(texts)
    if n == 0:
        return []
    if not (_HAS_SKLEARN and _HAS_BM25):
        return list(range(n))  # بدون تغییر

    # BM25
    tokenized_docs = [_preprocess_for_bm25(t) for t in texts]
    bm25 = BM25Okapi(tokenized_docs)
    bm25_scores = bm25.get_scores(_preprocess_for_bm25(query)).tolist()  # length=n
    bm25_norm = _normalize_scores(bm25_scores)

    # TF-IDF
    tf = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), analyzer="word")
    tf_mat = tf.fit_transform(texts)
    q_vec = tf.transform([query])
    sim = cosine_similarity(q_vec, tf_mat).flatten().tolist()
    tfidf_norm = _normalize_scores(sim)

    # Hybrid
    hybrid = [(_W_BM25 * bm25_norm[i] + _W_TFIDF * tfidf_norm[i], i) for i in range(n)]
    hybrid.sort(key=lambda x: -x[0])
    return [i for (_score, i) in hybrid]


# ----------------------------------------------------
# رِرَنک نهایی: Hybrid محلی + AvalAI Cohere رِرَنک
# ----------------------------------------------------
def _rerank_pairs(query: str, candidates: List[Tuple[int, float, str]], store: Store, top_n: int) -> List[Tuple[int, float, str]]:
    """
    ورودی candidates همان خروجی اولیهٔ store.search_hybrid است [(chunk_id, score, tag), ...].
    این تابع:
      1) حداکثر K0 کاندید اول را می‌گیرد.
      2) Hybrid محلی (BM25+TF-IDF) را روی متن همین کاندیدها اجرا می‌کند → K1 تای برتر.
      3) این K1 را به AvalAI Cohere Rerank می‌فرستد → ترتیب نهایی.
      4) top_n اول را برمی‌گرداند (با همان tuple ساختار اصلی).
    """
    if not candidates:
        return []

    # K0: محدود کردن حجم اولیه برای سرعت
    pool = candidates[:max(top_n * 5, _LOCAL_HYBRID_CAND_K)]
    # متن هر chunk
    texts: List[str] = []
    rows: List[Tuple[int, float, str]] = []
    for cid, sc, tag in pool:
        ch = store.get_chunk(cid)
        if not ch or not (ch.text or "").strip():
            continue
        texts.append(ch.text)
        rows.append((cid, sc, tag))

    if not rows:
        return []

    # مرحله Hybrid محلی
    order_local = _local_hybrid_rank(query, texts)  # ایندکس‌های rows/texts
    k1 = min(len(order_local), max(top_n * 2, _LOCAL_HYBRID_TOP_K))
    order_local_top = order_local[:k1]

    # آماده برای AvalAI
    texts_top = [texts[i] for i in order_local_top]
    # خروجی AvalAI: ترتیب ایندکس داخل texts_top
    order_final_local_idx = AvalAIService.rerank_documents(query, texts_top, top_k=k1)
    # نگاشت به ایندکس rows اصلی
    final_rows_indices = [order_local_top[i] for i in order_final_local_idx if 0 <= i < k1]

    # تبدیل back به [(cid, sc, tag), ...]
    final_rows = [rows[i] for i in final_rows_indices][:top_n]
    return final_rows


# ----------------------------------------------------
# تعارض / تحلیل (مثل قبل)
# ----------------------------------------------------
def _pick_segments_evenly(chunks: List[Any], limit: int) -> List[str]:
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
    max_segments = int(getattr(config, "ANALYZE_MAX_SEGMENTS", 6))
    per_chunk_candidates = int(per_chunk_candidates or getattr(config, "PER_CHUNK_CANDIDATES", 2))
    final_k_conf = int(getattr(config, "CONFLICT_FINAL_K", 6))
    max_judgments = int(getattr(config, "CONFLICT_JUDGMENTS", 5))

    candidate_segments = _pick_segments_evenly(uploaded_chunks, max_segments)
    if not candidate_segments:
        return []

    collected: List[Tuple[int, float, str]] = []
    for seg_text in candidate_segments:
        hits = store.search_hybrid(seg_text, vec_k=config.VEC_K, bm25_k=config.BM25_K)
        # اینجا هم از ریرنک جدید استفاده کنیم، اما خروجی محدود (per_chunk_candidates)
        hits = _rerank_pairs(seg_text, hits, store, per_chunk_candidates)
        collected.extend(hits)

    # dedupe by chunk_id
    best_map: Dict[int, Tuple[float, str]] = {}
    for cid, sc, tag in collected:
        if cid not in best_map or sc > best_map[cid][0]:
            best_map[cid] = (sc, tag)

    top_all = sorted([(cid, sc, tag) for cid, (sc, tag) in best_map.items()],
                     key=lambda x: -x[1])[:final_k_conf]

    judge_sys = (
        "قاضی تعارض متون حقوقی. فقط بر اساس دو متن، مشخص کن تعارض (مغایرت) وجود دارد یا خیر. "
        "اگر تعارض هست، بند یا ماده متعارض را دقیق نشان بده و توضیح کوتاه بده."
    )

    uploaded_piece = candidate_segments[0] if candidate_segments else ""

    out: List[Dict[str, Any]] = []
    for cid, score, tag in top_all[:max_judgments]:
        ch = store.get_chunk(cid)
        if not ch:
            continue
        doc = store.get_document(ch.doc_id)
        try:
            doc_meta = (doc.meta and isinstance(doc.meta, str)) and json.loads(doc.meta) or {}
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
