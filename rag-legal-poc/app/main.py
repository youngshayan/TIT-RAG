# app/main.py
from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pathlib import Path
import json, uuid, shutil

from app import config
from app.store import Store
from app.llm import ChatClient
from app.ingest import _build_chunks, _load_text_from_path
from app.metadata import extract_doc_meta
from app.retrieval import summarize_text, find_conflicts_against_index, _rerank_pairs
from app.classify import classify_category
from app.notify import send_email

app = FastAPI(title="RAG Legal PoC", version="0.5.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # محدود کن در تولید
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons
store = Store()
chat = ChatClient()

@app.get("/")
def root():
    rows = int(store.index.ntotal if store.index is not None else 0)
    return {"ok": True, "message": "RAG Legal PoC is running", "index_rows": rows}

# ----------------- End-User: Upload (Analyze only) -----------------
@app.post("/upload")
async def upload_and_analyze(
    files: List[UploadFile] = File(...),
    per_chunk_candidates: int = Form(3),
    final_k: int = Form(15)
):
    results: List[Dict[str, Any]] = []
    for uf in files:
        tmp_path = config.TMP_DIR / uf.filename
        with open(tmp_path, "wb") as w:
            w.write(await uf.read())
        try:
            text = _load_text_from_path(tmp_path)
        finally:
            try: tmp_path.unlink(missing_ok=True)
            except Exception: pass

        meta = extract_doc_meta(text) or {}
        meta["filename"] = uf.filename
        chunks = _build_chunks(text)
        summary_md = summarize_text(chat, text, meta)

        conflicts = find_conflicts_against_index(
            store=store,
            chatter=chat,
            uploaded_chunks=[{"text": c} for c in chunks],
            uploaded_meta=meta,
            per_chunk_candidates=per_chunk_candidates,
            final_k=final_k
        )
        results.append({
            "filename": uf.filename,
            "meta": meta,
            "summary": summary_md,
            "conflicts": conflicts
        })
    return {"analyzed": results}

# ----------------- End-User: Ask (with short history) --------------
@app.post("/ask")
async def ask_endpoint(
    query: str = Form(...),
    top_k: int = Form(5),
    history: Optional[str] = Form(None)
):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query is empty.")

    if store.index is None or store.index.ntotal == 0:
        return {"answer": "در حال حاضر هیچ سندی در پایگاه وجود ندارد. ابتدا اسناد را ingest کنید.", "citations": []}

    first_candidates = store.search_hybrid(
        query=query,
        vec_k=max(top_k * 3, config.VEC_K),
        bm25_k=max(top_k * 3, config.BM25_K)
    )
    reranked = _rerank_pairs(query, first_candidates, store, top_k)
    if not reranked:
        return {"answer": "سندی مرتبط پیدا نشد.", "citations": []}

    context_snippets: List[str] = []
    citations: List[Dict[str, Any]] = []
    used_doc_ids: set[int] = set()

    for cid, sc, tag in reranked[:top_k]:
        ch = store.get_chunk(cid)
        if not ch:
            continue
        doc = store.get_document(ch.doc_id)
        try:
            doc_meta = (doc.meta and isinstance(doc.meta, str)) and json.loads(doc.meta) or {}
        except Exception:
            doc_meta = {}
        snippet = ch.text.strip().replace("\n", " ")
        context_snippets.append(f"■ {snippet[:700]}")
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

    history_text = ""
    if history:
        try:
            turns = json.loads(history)
            turns = [t for t in turns if "role" in t and "content" in t][-3:]
            if turns:
                lines = []
                for t in turns:
                    role = "کاربر" if t["role"] == "user" else "دستیار"
                    lines.append(f"{role}: {str(t['content'])[:1200]}")
                history_text = "گفتگو تا این لحظه:\n" + "\n".join(lines) + "\n\n"
        except Exception:
            pass

    system_msg = (
        "تو یک دستیار حقوقی بانکی فارسی هستی. فقط بر اساس شواهد زیر پاسخ بده. "
        "اگر اطلاعات کافی نیست، بگو «اطلاعی ندارم» یا «نیازمند سند بیشتر است». "
        "از حدس زدن خودداری کن. پاسخ را شفاف و منظم ارائه بده.\n" + config.DISCLAIMER
    )
    user_msg = (
        f"{history_text}"
        f"پرسش:\n{query}\n\n"
        "شواهد مرتبط (گزیده):\n" + "\n".join(context_snippets[:top_k]) + "\n\n"
        "فقط با تکیه بر همین شواهد پاسخ بده."
    )
    answer = chat.chat(system=system_msg, user=user_msg)
    return {"answer": answer, "citations": citations}

# ----------------- Admin: Login via token + Upload/Index -----------
@app.post("/admin/upload_and_index")
async def admin_upload_and_index(
    files: List[UploadFile] = File(...),
    x_admin_token: str = Header(None),
    auto_category: bool = Form(True),
    category: Optional[str] = Form(None),
):
    # احراز هویت ساده ادمین
    if not x_admin_token or x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    out: List[Dict[str, Any]] = []
    base_dir = config.FILES_DIR
    base_dir.mkdir(parents=True, exist_ok=True)

    for uf in files:
        # 0) ذخیره موقت
        tmp_path = config.TMP_DIR / f"{uuid.uuid4().hex}__{uf.filename}"
        with open(tmp_path, "wb") as w:
            w.write(await uf.read())
        print(f"[ADMIN] received file: {uf.filename} -> {tmp_path}")

        # 1) متن (PDF→OCR/هوک شما | TXT→مستقیم)
        text = _load_text_from_path(tmp_path)
        print(f"[ADMIN] text length: {len(text)}")

        # 2) متادیتا
        meta = extract_doc_meta(text) or {}
        meta["filename"] = uf.filename

        # 3) دسته‌بندی: خودکار یا دستی
        if not auto_category and category:
            cat = category if category in config.CATEGORIES else config.CATEGORIES[0]
        else:
            cat = classify_category(chat, text, meta)
        print(f"[ADMIN] category: {cat}")

        # 4) انتقال فایل به data/files/<cat>/
        cat_dir = base_dir / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        final_path = cat_dir / uf.filename
        try:
            shutil.move(str(tmp_path), final_path)
        except Exception:
            shutil.copy(str(tmp_path), final_path)
            try: tmp_path.unlink(missing_ok=True)
            except Exception: pass
        print(f"[ADMIN] stored at: {final_path}")

        # 5) ایندکس در پایگاه (استفاده از Store موجود)
        chunks = _build_chunks(text)
        title = meta.get("title") or meta.get("number") or uf.filename
        # ← مهم: این دو خط بجای add_document + add_chunk از API خودت استفاده می‌کند
        doc_id = store.add_document_with_chunks(title or uf.filename, final_path, chunks, text)
        store.index_doc(doc_id)
        print(f"[ADMIN] indexed doc_id={doc_id} with {len(chunks)} chunks")

        # 6) ایمیل نوتیف
        recips_raw = config.CATEGORY_RECIPIENTS.get(cat, "")
        recipients = [e.strip() for e in recips_raw.split(",") if e.strip()]
        subject = f"«{cat}» - سند جدید: {uf.filename}"
        body = (
            f"سند جدید در دسته «{cat}» آپلود و ایندکس شد.\n\n"
            f"عنوان/شماره: {title}\n"
            f"مسیر: {final_path}\n"
            f"متادیتا: {json.dumps(meta, ensure_ascii=False)}\n"
        )
        email_ok = send_email(subject, body, recipients)
        print(f"[ADMIN] email notified={bool(email_ok)} to {recipients}")

        out.append({
            "filename": uf.filename,
            "category": cat,
            "indexed": True,
            "notified": bool(email_ok),
            "recipients": recipients,
            "stored_path": str(final_path)
        })

    return {"ok": True, "indexed": out}