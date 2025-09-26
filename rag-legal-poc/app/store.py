# app/store.py
from __future__ import annotations
from typing import Optional, List, Dict, Tuple
from sqlmodel import Field, SQLModel, create_engine, Session, select
from datetime import datetime
from pathlib import Path
import json
import re

import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from app import config
from app.metadata import extract_doc_meta, extract_chunk_meta


# ---------------------- DB Models ----------------------
class Document(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    source_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    meta: Optional[str] = None  # JSON


class Chunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    doc_id: int = Field(index=True)
    position: int
    text: str
    meta: Optional[str] = None  # JSON


# ---------------------- Store ----------------------
class Store:
    def __init__(self):
        self.engine = create_engine(f"sqlite:///{config.SQLITE_PATH}")
        SQLModel.metadata.create_all(self.engine)

        # Embedding model
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.dim = self.model.get_sentence_embedding_dimension()

        # FAISS (IndexIDMap over IndexFlatIP for cosine via L2-normalized vectors)
        self.index: Optional[faiss.Index] = None
        self.id_to_chunk: Dict[int, int] = {}
        self._load_faiss()
        self._ensure_idmap()

        # BM25
        self.bm25: Optional[BM25Okapi] = None
        self.bm25_tokens: List[List[str]] = []
        self._load_bm25()

    def add_document(self, title: str, source_path: str, meta: dict) -> int:
        """سند جدید را در جدول documents درج می‌کند و doc_id برمی‌گرداند."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO documents (title, source_path, meta) VALUES (?,?,?)",
            (title, source_path, json.dumps(meta, ensure_ascii=False))
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_chunk(self, doc_id: int, text: str, chunk_index: int) -> int:
        """چانک جدید را درج می‌کند و chunk_id برمی‌گرداند (و FTS/BM25 را به‌روز می‌کند اگر داری)."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO chunks (doc_id, chunk_index, text) VALUES (?,?,?)",
            (doc_id, chunk_index, text)
        )
        chunk_id = int(cur.lastrowid)
        # اگر FTS5 داری:
        try:
            cur.execute("INSERT INTO chunks_fts(rowid, text) VALUES (?, ?)", (chunk_id, text))
        except Exception:
            pass
        self.conn.commit()
        return chunk_id

    def _ensure_idmap(self):
        import faiss
        if self.index is None:
            return
        if not isinstance(self.index, faiss.IndexIDMap) and not isinstance(self.index, faiss.IndexIDMap2):
            # wrap current index (e.g., Flat or HNSW) with IDMap
            self.index = faiss.IndexIDMap(self.index)

    def add_vector_for_chunk(self, chunk_id: int, text: str):
        """امبدینگ بگیر و به FAISS با ID برابر chunk_id اضافه کن."""
        self._ensure_idmap()
        vec = self.embedder.encode([text])  # ← فرض: sentence-transformers
        if hasattr(vec, "tolist"):  # numpy array
            vec = np.array(vec, dtype="float32")
        else:
            vec = np.array(vec, dtype="float32")
        if vec.ndim == 1:
            vec = vec.reshape(1, -1).astype("float32")
        ids = np.array([chunk_id], dtype="int64")
        self.index.add_with_ids(vec, ids)
        # ذخیره ایندکس
        faiss.write_index(self.index, str(self.index_path))

    def add_bm25_for_chunk(self, chunk_id: int, text: str):
        """اگر موتور BM25 جدا داری، در اینجا ایندکس کن؛ اگر از FTS5 استفاده می‌کنی، add_chunk کافی بود."""
        # اگر از Rank-BM25 در حافظه استفاده می‌کنی، باید مدل را مجدد بازسازی کنی (سنگین است).
        # برای PoC: از FTS5 بالا استفاده می‌کنیم؛ پس این متد می‌تواند No-Op باشد.
        return
    # ---------------------- FAISS ----------------------
    def _new_faiss(self):
        base = faiss.IndexFlatIP(self.dim)
        self.index = faiss.IndexIDMap(base)
        self.id_to_chunk = {}

    def _load_faiss(self):
        try:
            if config.FAISS_INDEX_PATH.exists() and config.FAISS_MAP_PATH.exists():
                idx = faiss.read_index(str(config.FAISS_INDEX_PATH))
                # ensure it's an IDMap
                if not isinstance(idx, faiss.IndexIDMap2) and not isinstance(idx, faiss.IndexIDMap):
                    idx = faiss.IndexIDMap(idx)
                self.index = idx
                self.id_to_chunk = json.loads(config.FAISS_MAP_PATH.read_text("utf-8"))
                self.id_to_chunk = {int(k): int(v) for k, v in self.id_to_chunk.items()}
            else:
                self._new_faiss()
                self._save_faiss()
        except Exception:
            self._new_faiss()
            self._save_faiss()

    def _save_faiss(self):
        faiss.write_index(self.index, str(config.FAISS_INDEX_PATH))
        config.FAISS_MAP_PATH.write_text(
            json.dumps({int(k): int(v) for k, v in self.id_to_chunk.items()}, ensure_ascii=False),
            encoding="utf-8"
        )

    # ---------------------- BM25 ----------------------
    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[\w\u0600-\u06FF]+", text)

    def _load_bm25(self):
        try:
            if config.BM25_CORPUS_PATH.exists():
                data = json.loads(config.BM25_CORPUS_PATH.read_text("utf-8"))
                self.bm25_tokens = data.get("tokens", [])
                if self.bm25_tokens:
                    self.bm25 = BM25Okapi(self.bm25_tokens)
            else:
                self.bm25_tokens = []
                self.bm25 = None
        except Exception:
            self.bm25_tokens = []
            self.bm25 = None

    def _save_bm25(self):
        config.BM25_CORPUS_PATH.write_text(
            json.dumps({"tokens": self.bm25_tokens}, ensure_ascii=False),
            encoding="utf-8"
        )

    # ---------------------- CRUD ----------------------
    def add_document_with_chunks(self, title: str, source_path: Path, chunks: List[str], full_text: str) -> int:
        doc_meta = extract_doc_meta(full_text)
        with Session(self.engine) as s:
            doc = Document(
                title=title or source_path.stem,
                source_path=str(source_path),
                meta=json.dumps(doc_meta, ensure_ascii=False),
            )
            s.add(doc)
            s.commit()
            s.refresh(doc)

            rows = []
            for i, ch in enumerate(chunks):
                cmeta = extract_chunk_meta(ch)
                rows.append(Chunk(
                    doc_id=doc.id,
                    position=i,
                    text=ch,
                    meta=json.dumps(cmeta, ensure_ascii=False),
                ))
            s.add_all(rows)
            s.commit()
            return doc.id

    def get_doc_chunks(self, doc_id: int) -> List[Chunk]:
        with Session(self.engine) as s:
            stmt = select(Chunk).where(Chunk.doc_id == doc_id).order_by(Chunk.position.asc())
            return list(s.exec(stmt))

    def get_chunk(self, chunk_id: int) -> Optional[Chunk]:
        with Session(self.engine) as s:
            return s.get(Chunk, chunk_id)

    def get_document(self, doc_id: int) -> Optional[Document]:
        with Session(self.engine) as s:
            return s.get(Document, doc_id)

    def get_document_by_chunk(self, chunk_id: int) -> Optional[Document]:
        ch = self.get_chunk(chunk_id)
        if not ch:
            return None
        return self.get_document(ch.doc_id)

    # ---------------------- Index Build / Update ----------------------
    def index_doc(self, doc_id: int):
        chunks = self.get_doc_chunks(doc_id)
        if not chunks:
            return

        texts = [c.text for c in chunks]
        vec = self.model.encode(texts, normalize_embeddings=True).astype("float32")
        start_id = len(self.id_to_chunk)
        ids = np.arange(start_id, start_id + vec.shape[0]).astype("int64")

        self.index.add_with_ids(vec, ids)
        for i, ch in enumerate(chunks):
            self.id_to_chunk[int(ids[i])] = int(ch.id)
        self._save_faiss()

        tokens_list = [self._tokenize(t) for t in texts]
        self.bm25_tokens.extend(tokens_list)
        self.bm25 = BM25Okapi(self.bm25_tokens)
        self._save_bm25()

    # ---------------------- Hybrid Search ----------------------
    def search_hybrid(self, query: str, vec_k: int, bm25_k: int) -> List[Tuple[int, float, str]]:
        out: List[Tuple[int, float, str]] = []

        # Vector
        if self.index is not None and self.index.ntotal > 0:
            qv = self.model.encode([query], normalize_embeddings=True).astype("float32")
            scores, idxs = self.index.search(qv, min(vec_k, max(1, self.index.ntotal)))
            vec_hits = []
            for i, s in zip(idxs[0], scores[0]):
                if i == -1:
                    continue
                cid = self.id_to_chunk.get(int(i))
                if cid is not None:
                    vec_hits.append((cid, float(s), "vec"))
        else:
            vec_hits = []

        # BM25
        bm_hits = []
        if self.bm25 and self.bm25_tokens:
            scores = self.bm25.get_scores(self._tokenize(query))
            if len(scores):
                k = min(bm25_k, len(scores))
                top_idx = np.argpartition(-scores, k - 1)[:k]
                top_idx = top_idx[np.argsort(-scores[top_idx])]
                ordered_ids = [cid for _, cid in sorted(self.id_to_chunk.items(), key=lambda x: x[0])]
                for bi in top_idx:
                    if 0 <= bi < len(ordered_ids):
                        bm_hits.append((ordered_ids[bi], float(scores[bi]), "bm25"))

        merged: Dict[int, Tuple[float, str]] = {}
        for cid, sc, tag in bm_hits + vec_hits:
            if cid not in merged or sc > merged[cid][0]:
                merged[cid] = (sc, tag)

        out = sorted([(cid, sc, tag) for cid, (sc, tag) in merged.items()],
                     key=lambda x: -x[1])
        return out
