# app/main.py
from __future__ import annotations

import json, uuid, shutil, logging, time
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks

from app.graph import build_answer_graph
from app import config
from app.store import Store
from app.llm import ChatClient
from app.ingest import _build_chunks, _load_text_from_path, ingest_file
from app.metadata import extract_doc_meta
from app.retrieval import (
    summarize_text,
    find_conflicts_against_index,
    _rerank_pairs,
    answer_with_context,   # ← اضافه شد
)
from app.classify import classify_category
from app.notify import send_email

try:
    from reembed_all import main as reembed_all_main  # اختیاری
except Exception:
    reembed_all_main = None

logger = logging.getLogger("rag")
logger.setLevel(logging.INFO)

app = FastAPI(title="RAG Legal PoC", version="0.7.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def dispatch(request: Request, call_next):
    t0 = time.time()
    try:
        response = await call_next(request)
    except Exception as e:
        dt = (time.time() - t0) * 1000
        logger.exception(f"[HTTP][EXC] {request.method} {request.url.path} in {dt:.1f} ms: {e}")
        raise
    dt = (time.time() - t0) * 1000
    logger.info(f"[HTTP] {request.method} {request.url.path} -> {response.status_code} in {dt:.1f} ms")
    return response

# Singletons
store = Store()
chat = ChatClient()


@app.get("/health")
def health():
    rows = int(store.index.ntotal if store.index is not None else 0)
    logger.info(f"[HEALTH] index_rows={rows}")
    return {"ok": True, "index_rows": rows, "version": app.version}


@app.get("/")
def root():
    rows = int(store.index.ntotal if store.index is not None else 0)
    logger.info(f"[ROOT] index_rows={rows}")
    return {"ok": True, "message": "RAG Legal PoC is running", "index_rows": rows, "version": app.version}

# ----------------- End-User: Upload (Analyze only) -----------------
@app.post("/upload")
async def upload_and_analyze(
    files: List[UploadFile] = File(...),
    per_chunk_candidates: int = Form(None),
    final_k: int = Form(None)
):

    if per_chunk_candidates is None:
        per_chunk_candidates = int(getattr(config, "PER_CHUNK_CANDIDATES", 2))
    if final_k is None:
        final_k = int(getattr(config, "CONFLICT_FINAL_K", 6))

    logger.info(f"[UPLOAD] received {len(files)} file(s); per_chunk={per_chunk_candidates}, final_k={final_k}")
    results: List[Dict[str, Any]] = []
    for uf in files:
        tmp_path = config.TMP_DIR / uf.filename
        with open(tmp_path, "wb") as w:
            w.write(await uf.read())
        logger.info(f"[UPLOAD] tmp saved: {tmp_path} (name={uf.filename})")
        try:
            text = _load_text_from_path(tmp_path)
            logger.info(f"[UPLOAD] text_len={len(text)} for file={uf.filename}")
            chunks = _build_chunks(text)
            logger.info(f"[UPLOAD] chunks={len(chunks)} for file={uf.filename}")

            meta = extract_doc_meta(text) or {}
            meta["filename"] = uf.filename

            t0 = time.time()
            summary_md = summarize_text(chat, text, meta)
            logger.info(f"[UPLOAD] summary_done in {(time.time()-t0)*1000:.1f} ms for {uf.filename}")

            uploaded_list = [{"text": c} for c in chunks]  # برای فیکس تایپ
            conflicts = find_conflicts_against_index(
                store=store,
                chatter=chat,
                uploaded_chunks=uploaded_list,
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
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
    return {"analyzed": results}

# ----------------- End-User: Ask (Context-aware with session) --------------
@app.post("/ask")
async def ask_endpoint(
    query: str = Form(...),
    top_k: int = Form(5),
    history: Optional[str] = Form(None),
    sid: Optional[str] = Form(None),
):
    qlog = (query or "")[:80].replace("\n", " ")
    logger.info(f"[ASK] query='{qlog}...' top_k={top_k} sid={sid or '-'}")


    default_answer: str = "نتوانستم پاسخ تولید کنم. لطفاً دوباره تلاش کنید یا پرسش را دقیق‌تر بیان کنید."
    empty_graph = {"elements": [], "kpis": {"sources": 0, "keywordCoverage": 0.0, "confidence": 0.0}}

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query is empty.")


    if store.index is None or store.index.ntotal == 0:
        try:
            graph = build_answer_graph(query, [], store, top_k=0)
        except Exception as ge:
            logger.warning(f"[ASK][GRAPH] build failed on empty index: {ge}")
            graph = empty_graph
        return {
            "answer": "در حال حاضر هیچ سندی در پایگاه وجود ندارد. ابتدا اسناد را ingest کنید.",
            "citations": [],
            "graph": graph,
        }

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

    try:
        out = answer_with_context(
            store=store,
            chatter=chat,
            question=(history_text + query) if history_text else query,
            top_k=top_k or 6,
            sid=sid,
        )
        answer = out.get("answer") or default_answer
        citations = out.get("citations") or []
        used_doc_ids = set(out.get("used_doc_ids") or [])
    except Exception as e:
        logger.exception(f"[ASK] answer_with_context failed: {e}")

        return {"answer": default_answer, "citations": [], "graph": empty_graph}


    try:

        restrict: Optional[Set[int]] = used_doc_ids if used_doc_ids else None
        first_candidates = store.search_hybrid(
            query=query,
            vec_k=max(top_k * 3, config.VEC_K),
            bm25_k=max(top_k * 3, config.BM25_K),
            restrict_doc_ids=restrict,
            allow_broaden=True,
        )
        reranked = _rerank_pairs(query, first_candidates, store, top_k)
        graph = build_answer_graph(query, reranked, store, top_k=top_k)
    except Exception as ge:
        logger.warning(f"[ASK][GRAPH] build failed: {ge}")
        graph = empty_graph

    return {
        "answer": answer,
        "citations": citations,
        "graph": graph,
    }

# ----------------- Helpers for admin post-actions ------------------
def _ingest_paths_after_admin(paths: List[Path]):
    st = Store()
    done = []
    for p in paths:
        try:
            doc_id = ingest_file(st, p, title=p.stem)
            logger.info(f"[ADMIN][INGEST] {p.name} -> doc_id={doc_id}")
            done.append(str(p))
        except Exception as e:
            logger.exception(f"[ADMIN][INGEST][ERR] {p}: {e}")
    logger.info(f"[ADMIN][INGEST] completed for {len(done)} file(s): {done}")

def _run_reembed_background():
    if reembed_all_main is None:
        logger.warning("[ADMIN][REEMBED] reembed_all.main not importable; skipped.")
        return
    try:
        logger.info("[ADMIN][REEMBED] started...")
        reembed_all_main()
        logger.info("[ADMIN][REEMBED] finished.")
    except Exception as e:
        logger.exception(f"[ADMIN][REEMBED][ERR] {e}")

# ----------------- Admin: Login via token + Upload/Index -----------
@app.post("/admin/upload_and_index")
async def admin_upload_and_index(
    background: BackgroundTasks,
    files: List[UploadFile] = File(...),
    x_admin_token: str = Header(None),
    auto_category: bool = Form(True),
    category: Optional[str] = Form(None),
):
    if not x_admin_token or x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    logger.info(f"[ADMIN] received {len(files)} file(s) | auto_category={auto_category} category={category}")
    out: List[Dict[str, Any]] = []
    base_dir = config.FILES_DIR
    base_dir.mkdir(parents=True, exist_ok=True)

    new_final_paths: List[Path] = []

    for uf in files:
        tmp_path = config.TMP_DIR / f"{uuid.uuid4().hex}__{uf.filename}"
        with open(tmp_path, "wb") as w:
            w.write(await uf.read())
        logger.info(f"[ADMIN] tmp saved: {tmp_path} (name={uf.filename})")

        text = _load_text_from_path(tmp_path)
        logger.info(f"[ADMIN] text_len={len(text)} for {uf.filename}")

        meta = extract_doc_meta(text) or {}
        meta["filename"] = uf.filename

        if not auto_category and category:
            cat = category if category in config.CATEGORIES else config.CATEGORIES[0]
        else:
            cat = classify_category(chat, text, meta)
        logger.info(f"[ADMIN] category={cat}")

        cat_dir = base_dir / cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        final_path = cat_dir / uf.filename
        try:
            shutil.move(str(tmp_path), final_path)
        except Exception:
            shutil.copy(str(tmp_path), final_path)
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
        logger.info(f"[ADMIN] stored at: {final_path}")
        new_final_paths.append(final_path)

        if config.ADMIN_INLINE_INDEX:
            chunks = _build_chunks(text)
            title = meta.get("title") or meta.get("number") or uf.filename
            doc_id = store.add_document_with_chunks(title or uf.filename, final_path, chunks, text)
            store.index_doc(doc_id)
            logger.info(f"[ADMIN] inline-indexed doc_id={doc_id} with {len(chunks)} chunks")

        recips_raw = config.CATEGORY_RECIPIENTS.get(cat, "")
        recipients = [e.strip() for e in recips_raw.split(",") if e.strip()]
        subject = f"«{cat}» - سند جدید: {uf.filename}"
        body = (
            f"سند جدید در دسته «{cat}» آپلود شد.\n\n"
            f"عنوان/شماره: {meta.get('title') or meta.get('number') or uf.filename}\n"
            f"مسیر: {final_path}\n"
            f"متادیتا: {json.dumps(meta, ensure_ascii=False)}\n"
        )
        email_ok = send_email(subject, body, recipients)
        logger.info(f"[ADMIN] email notified={bool(email_ok)} to {recipients}")

        out.append({
            "filename": uf.filename,
            "category": cat,
            "indexed": bool(config.ADMIN_INLINE_INDEX),
            "notified": bool(email_ok),
            "recipients": recipients,
            "stored_path": str(final_path)
        })

    if config.RUN_INGEST_FOR_NEW_FILES and not config.ADMIN_INLINE_INDEX:
        background.add_task(_ingest_paths_after_admin, new_final_paths)

    if config.RUN_REEMBED_AFTER_ADMIN:
        background.add_task(_run_reembed_background)

    return {"ok": True, "indexed": out}


@app.post("/admin/reembed")
def admin_reembed(x_admin_token: str = Header(None)):
    if not x_admin_token or x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if reembed_all_main is None:
        raise HTTPException(status_code=500, detail="reembed_all.main not found")
    logger.info("[ADMIN][REEMBED] manual trigger started...")
    reembed_all_main()
    logger.info("[ADMIN][REEMBED] manual trigger finished.")
    return {"ok": True}

@app.post("/admin/ingest_folder")
def admin_ingest_folder(x_admin_token: str = Header(None)):
    if not x_admin_token or x_admin_token != config.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        from ingest_folder import main as ingest_folder_main
    except Exception:
        raise HTTPException(status_code=500, detail="ingest_folder.py not found")
    logger.info("[ADMIN][INGEST_FOLDER] manual trigger started...")
    ingest_folder_main()
    logger.info("[ADMIN][INGEST_FOLDER] manual trigger finished.")
    return {"ok": True}
