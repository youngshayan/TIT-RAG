# app/main.py
from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from pathlib import Path
import json

from app import config
from app.store import Store
from app.llm import ChatClient
from app.ingest import _build_chunks, _load_text_from_path
from app.metadata import extract_doc_meta
from app.retrieval import summarize_text, find_conflicts_against_index, _rerank_pairs

app = FastAPI(title="RAG Legal PoC", version="0.2.0")

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # در صورت نیاز محدود کن: ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Singletons ----------
store = Store()
chat = ChatClient()


# ---------- Health ----------
@app.get("/")
def root():
    rows = int(store.index.ntotal if store.index is not None else 0)
    return {
        "ok": True,
        "message": "RAG Legal PoC is running",
        "index_rows": rows,
    }


# =================================================================
# 1) Upload & Analyze (NO indexing): summary + conflict check
# =================================================================
@app.post("/upload")
async def upload_and_analyze(
    files: List[UploadFile] = File(...),
    per_chunk_candidates: int = Form(3),
    final_k: int = Form(15)
):
    """
    فایل‌ها را می‌گیرد، متن را استخراج و چانک می‌کند، خلاصه می‌دهد و
    نسبت به ایندکس موجود، تعارض‌ها را پیدا می‌کند—بدون افزودن به پایگاه.
    """
    results: List[Dict[str, Any]] = []

    for uf in files:
        # ذخیره‌ی موقت برای پردازش
        tmp_path = config.TMP_DIR / uf.filename
        with open(tmp_path, "wb") as w:
            w.write(await uf.read())

        try:
            # استخراج متن خام (txt/pdf)
            text = _load_text_from_path(tmp_path)
        finally:
            # حذف فایل موقت
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        # متادیتای سند (از متن)
        meta = extract_doc_meta(text) or {}
        meta["filename"] = uf.filename

        # چانکینگ
        chunks = _build_chunks(text)

        # خلاصه
        summary_md = summarize_text(chat, text, meta)

        # تعارض با ایندکس موجود
        conflicts = find_conflicts_against_index(
            store=store,
            chatter=chat,
            uploaded_chunks=chunks,
            uploaded_meta=meta,
            per_chunk_candidates=per_chunk_candidates,
            final_k=final_k
        )

        results.append({
            "filename": uf.filename,
            "meta": meta,
            "summary": summary_md,     # در فرانت با Markdown component رندر می‌شود
            "conflicts": conflicts     # سورس‌دهی انسانی: title + meta + source_path
        })

    return {"analyzed": results}


# =================================================================
# 2) Ask: RAG over existing index (with human-readable citations)
# =================================================================
@app.post("/ask")
async def ask_endpoint(
    query: str = Form(...),
    top_k: int = Form(5)
):
    """
    پرسش کاربر را بر اساس ایندکس موجود پاسخ می‌دهد.
    - Hybrid (FAISS + BM25) + CrossEncoder rerank
    - ساخت context انسانی و citations انسانی (نام فایل، صادرکننده، تاریخ، ...)
    """
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query is empty.")

    # اگر ایندکس خالی است
    if store.index is None or store.index.ntotal == 0:
        return {
            "answer": "در حال حاضر هیچ سندی در پایگاه وجود ندارد. ابتدا اسناد را ingest کنید.",
            "citations": []
        }

    # Hybrid search
    first_candidates = store.search_hybrid(
        query=query,
        vec_k=max(top_k * 3, config.VEC_K),
        bm25_k=max(top_k * 3, config.BM25_K)
    )

    # Rerank by CrossEncoder و انتخاب top_k
    reranked = _rerank_pairs(query, first_candidates, store, top_k)
    if not reranked:
        return {"answer": "سندی مرتبط پیدا نشد.", "citations": []}

    # آماده‌سازی context انسانی (چند تکه‌ی کوتاه)
    context_snippets: List[str] = []
    citations: List[Dict[str, Any]] = []
    used_doc_ids: set[int] = set()

    for cid, sc, tag in reranked[:top_k]:
        ch = store.get_chunk(cid)
        if not ch:
            continue
        doc = store.get_document(ch.doc_id)
        doc_meta = {}
        try:
            doc_meta = (doc.meta and isinstance(doc.meta, str)) and json.loads(doc.meta) or {}
        except Exception:
            doc_meta = {}

        # قطعه‌ی کوتاه برای LLM
        snippet = ch.text.strip().replace("\n", " ")
        context_snippets.append(f"■ {snippet[:700]}")

        # Citation انسانی (اسم فایل، صادرکننده، تاریخ، ... )
        if doc and ch.doc_id not in used_doc_ids:
            citations.append({
                "doc_id": ch.doc_id,
                "title": doc.title or "",
                "source_path": doc.source_path or "",
                "meta": doc_meta,
                "score": round(float(sc), 4),
                "method": tag
            })
            used_doc_ids.add(ch.doc_id)

    # ساخت پرامپت برای پاسخ
    system_msg = (
        "تو یک دستیار حقوقی بانکی فارسی هستی. فقط بر اساس شواهد زیر پاسخ بده. "
        "اگر اطلاعات کافی نیست، صادقانه بگو «اطلاعی ندارم» یا «نیازمند سند بیشتر است». "
        "از حدس زدن خودداری کن. پاسخ را شفاف و منظم ارائه بده.\n" + config.DISCLAIMER
    )
    user_msg = (
        f"پرسش:\n{query}\n\n"
        "شواهد مرتبط (گزیده):\n"
        + "\n".join(context_snippets[:top_k])
        + "\n\n"
        "فقط با تکیه بر همین شواهد پاسخ بده."
    )

    answer = chat.chat(system=system_msg, user=user_msg)
    return {
        "answer": answer,
        "citations": citations
    }


# =================================================================
# نکته:
# - اگر نیاز داری endpoint جداگانه برای «آپلود و ایندکس» داشته باشی،
#   می‌توانم /upload_and_index را هم اضافه کنم. فعلاً طبق نیاز، فقط /upload تحلیل می‌کند.
# =================================================================
