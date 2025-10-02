# app/ingest.py
from __future__ import annotations
from typing import List
from pathlib import Path
import tiktoken

from app import config
from app.utils_text import normalize_persian
from app.store import Store
from app.pdf_to_text_hook import pdf_to_text

def _chunk_by_tokens(text: str, tokens=None, overlap=None, model_name="gpt-4o-mini"):
    """
    چانک‌گذاری مبتنی بر توکن؛ مقداردهی از config با دیفالت‌های پیشنهاد شده.
    """
    if tokens is None:
        tokens = int(getattr(config, "CHUNK_TOKENS", 650))     # پیشنهاد: 600–700
    if overlap is None:
        overlap = int(getattr(config, "CHUNK_OVERLAP", 90))    # ~14%

    enc = tiktoken.get_encoding("cl100k_base")
    ids = enc.encode(text)
    chunks = []
    start = 0
    while start < len(ids):
        end = min(start + tokens, len(ids))
        piece = enc.decode(ids[start:end]).strip()
        if piece:
            chunks.append(piece)
        if end == len(ids):
            break
        start = max(0, end - overlap)
    return chunks

def _split_by_legal_structure(text: str):
    import re
    parts = re.split(r"(?=^(\s*(ماده|تبصره|بند)\s+\d+))", text, flags=re.MULTILINE)
    if len(parts) <= 1:
        return None
    chunks, buf = [], ""
    for p in parts:
        if re.match(r"^\s*(ماده|تبصره|بند)\s+\d+", p or ""):
            if buf.strip():
                chunks.append(buf.strip())
            buf = p
        else:
            buf += p
    if buf.strip():
        chunks.append(buf.strip())
    return chunks

def _build_chunks(text: str) -> List[str]:

    tokens = int(getattr(config, "CHUNK_TOKENS", 650))
    overlap = int(getattr(config, "CHUNK_OVERLAP", 90))

    structural = _split_by_legal_structure(text)
    if structural and sum(len(s) for s in structural) > 0:
        out = []
        for seg in structural:
            out.extend(_chunk_by_tokens(seg, tokens=tokens, overlap=overlap))
        return out
    return _chunk_by_tokens(text, tokens=tokens, overlap=overlap)

def _load_text_from_path(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        txt = pdf_to_text(path)
    else:
        txt = path.read_text("utf-8", errors="ignore")
    txt = normalize_persian(txt)
    return txt

def ingest_file(store: Store, file_path: Path, title: str = None) -> int:
    full_text = _load_text_from_path(file_path)
    chunks = _build_chunks(full_text)
    doc_id = store.add_document_with_chunks(title or file_path.stem, file_path, chunks, full_text)
    store.index_doc(doc_id)
    return doc_id
