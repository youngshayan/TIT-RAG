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
from app.utils_text import normalize_persian


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

        # Embedding model (e5)
        self.model = SentenceTransformer(config.EMBEDDING_MODEL)
        self.dim = self.model.get_sentence_embedding_dimension()

        # FAISS (IndexIDMap over IndexFlatIP for cosine via L2-normalized vectors)
        self.index: Optional[faiss.Index] = None
        # map: faiss-vector-id -> chunk_id
        self.id_to_chunk: Dict[int, int] = {}
        self._load_faiss()
        self._ensure_idmap()

        # BM25 (in-memory)
        self.bm25: Optional[BM25Okapi] = None
        # ترتیب این لیست باید با ترتیب id_to_chunk (sort by vector-id asc) سازگار بماند
        self.bm25_tokens: List[List[str]] = []
        self._load_bm25()

    # ---------------------- small utils ----------------------
    def _ensure_idmap(self):
        if self.index is None:
            return
        if not isinstance(self.index, faiss.IndexIDMap) and not isinstance(self.index, faiss.IndexIDMap2):
            self.index = faiss.IndexIDMap(self.index)

    # ---------------------- FAISS ----------------------
    def _new_faiss(self):
        base = faiss.IndexFlatIP(self.dim)
        self.index = faiss.IndexIDMap(base)
        self.id_to_chunk = {}

    def _load_faiss(self):
        try:
            if config.FAISS_INDEX_PATH.exists() and config.FAISS_MAP_PATH.exists():
                idx = faiss.read_index(str(config.FAISS_INDEX_PATH))
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

    def _reset_faiss(self):
        self._new_faiss()
        self._save_faiss()

    def _init_faiss(self, dim: int):
        base = faiss.IndexFlatIP(dim)
        self.index = faiss.IndexIDMap(base)
        self.id_to_chunk = {}

    # ---------------------- BM25 ----------------------
    def _tokenize(self, text) -> List[str]:
        # ایمن در برابر ورودی dict (برای موارد اشتباه)، فقط متن را استخراج می‌کند
        if isinstance(text, dict):
            text = text.get("text", "")
        text = text or ""
        return re.findall(r"[\w\u0600-\u06FF]+", str(text))

    def _load_bm25(self):
        try:
            if config.Bm25_CORPUS_PATH.exists():
                data = json.loads(config.Bm25_CORPUS_PATH.read_text("utf-8"))
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
        config.Bm25_CORPUS_PATH.write_text(
            json.dumps({"tokens": self.bm25_tokens}, ensure_ascii=False),
            encoding="utf-8"
        )

    def _reset_bm25(self):
        self.bm25_tokens = []
        self.bm25 = None
        self._save_bm25()

    def _rebuild_bm25_from_db(self):
        with Session(self.engine) as s:
            stmt = select(Chunk).order_by(Chunk.id.asc())
            rows = list(s.exec(stmt))
        # توجه: ترتیب BM25 باید با ترتیب بردارها منطبق باشد؛
        # ما mappingِ faiss-id -> chunk_id را داریم، بنابراین لیست چانک‌ها را بر اساس faiss-id می‌چینیم.
        ordered = []
        for vec_id, ch_id in sorted(self.id_to_chunk.items(), key=lambda x: x[0]):
            ch = next((r for r in rows if r.id == ch_id), None)
            if ch:
                ordered.append(ch.text)
        self.bm25_tokens = [self._tokenize(t) for t in ordered]
        self.bm25 = BM25Okapi(self.bm25_tokens)

    # ---------------------- CRUD ----------------------
    def add_document_with_chunks(self, title: str, source_path: Path, chunks: List[str], full_text: str) -> int:
        doc_meta = extract_doc_meta(full_text)
        with Session(self.engine) as s:
            doc = Document(
                title=title or (source_path.stem if source_path else "Untitled"),
                source_path=str(source_path) if source_path else "",
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
        """
        - چانک‌ها را از DB می‌خواند
        - با prefix 'passage: ' و نرمال‌سازی فارسی امبد می‌کند
        - به FAISS (IDMap) با شناسه‌های پیوسته اضافه می‌کند
        - BM25 را با همان ترتیب بازسازی/به‌روز می‌کند
        """
        chunks = self.get_doc_chunks(doc_id)
        if not chunks:
            return

        texts = [normalize_persian(c.text or "") for c in chunks]
        passages = [f"passage: {t}" for t in texts]
        vec = self.model.encode(passages, normalize_embeddings=True, convert_to_numpy=True).astype("float32")

        start_id = len(self.id_to_chunk)
        ids = np.arange(start_id, start_id + vec.shape[0]).astype("int64")

        self.index.add_with_ids(vec, ids)
        for i, ch in enumerate(chunks):
            self.id_to_chunk[int(ids[i])] = int(ch.id)
        self._save_faiss()

        # BM25 – به همان ترتیب vector-idها نگه داریم:
        tokens_list = [self._tokenize(t) for t in texts]
        self.bm25_tokens.extend(tokens_list)
        self.bm25 = BM25Okapi(self.bm25_tokens)
        self._save_bm25()

    # ---------------------- Hybrid Search ----------------------
    def search_hybrid(self, query: str, vec_k: int, bm25_k: int) -> List[Tuple[int, float, str]]:
        out: List[Tuple[int, float, str]] = []

        # نرمال‌سازی کوئری
        qn = normalize_persian(query or "")

        # Vector (e5 needs 'query: ')
        vec_hits = []
        if self.index is not None and self.index.ntotal > 0:
            qv = self.model.encode([f"query: {qn}"], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
            scores, idxs = self.index.search(qv, min(vec_k, max(1, self.index.ntotal)))
            for i, s in zip(idxs[0], scores[0]):
                if i == -1:
                    continue
                cid = self.id_to_chunk.get(int(i))
                if cid is not None:
                    vec_hits.append((cid, float(s), "vec"))

        # BM25
        bm_hits = []
        if self.bm25 and self.bm25_tokens:
            scores = self.bm25.get_scores(self._tokenize(qn))
            if len(scores):
                k = min(bm25_k, len(scores))
                top_idx = np.argpartition(-scores, k - 1)[:k]
                top_idx = top_idx[np.argsort(-scores[top_idx])]
                # mapping: vector-id ascending -> chunk_id
                ordered_ids = [cid for _, cid in sorted(self.id_to_chunk.items(), key=lambda x: x[0])]
                for bi in top_idx:
                    if 0 <= bi < len(ordered_ids):
                        bm_hits.append((ordered_ids[bi], float(scores[bi]), "bm25"))

        # merge
        merged: Dict[int, Tuple[float, str]] = {}
        for cid, sc, tag in bm_hits + vec_hits:
            if cid not in merged or sc > merged[cid][0]:
                merged[cid] = (sc, tag)

        out = sorted([(cid, sc, tag) for cid, (sc, tag) in merged.items()],
                     key=lambda x: -x[1])
        return out

    # ---------------------- Compatibility shim ----------------------
    def add_document(self, title: str, source_path, full_text: str = "", meta: dict | None = None) -> int:
        """
        برای سازگاری با کدهای قدیمی:
        اگر full_text خالی باشد، متن فایل را می‌خوانیم، chunk می‌کنیم و وارد می‌کنیم.
        """
        from app.ingest import _build_chunks, _load_text_from_path

        spath = Path(source_path) if source_path is not None else None
        if not full_text and spath and spath.exists():
            full_text = _load_text_from_path(spath)

        chunks = _build_chunks(full_text or "")
        doc_id = self.add_document_with_chunks(title or (spath.stem if spath else "Untitled"), spath, chunks,
                                               full_text or "")
        return doc_id

    # ---------------------- Re-embed all (optional utility) ----------------------
    def rebuild_all_indexes_from_db(self, text_prefix: str = "passage: ", normalize_fn=None):
        """
        کل چانک‌ها را از sqlite می‌خواند، با prefix جدید امبد می‌کند،
        FAISS و BM25 را از نو می‌سازد.
        """
        with Session(self.engine) as s:
            stmt = select(Chunk.id, Chunk.text).order_by(Chunk.id.asc())
            rows = list(s.exec(stmt))

        if not rows:
            self._reset_faiss()
            self._reset_bm25()
            return

        texts = []
        chunk_ids = []
        for cid, t in rows:
            t2 = normalize_fn(t) if normalize_fn else (t or "")
            texts.append(f"{text_prefix}{t2}")
            chunk_ids.append(int(cid))

        # encode in batches
        batch = 256
        vecs = []
        for i in range(0, len(texts), batch):
            part = self.model.encode(texts[i:i+batch], normalize_embeddings=True, convert_to_numpy=True)
            vecs.append(part)
        mat = np.vstack(vecs).astype("float32")

        # FAISS fresh
        self._reset_faiss()
        self._init_faiss(dim=mat.shape[1])
        ids = np.array(chunk_ids, dtype="int64")
        self.index.add_with_ids(mat, ids)
        # id_to_chunk باید mapِ vector-id -> chunk_id باشد، اما الان ids = chunk_id هاست.
        # پس باید vector-id ها را از 0..N-1 تنظیم کنیم. ساده‌ترین راه:
        # بخاطر IndexIDMap، وقتی add_with_ids می‌زنیم، vector-id داخلی 0..N-1 می‌شود و ما IDMap را خودمان کنترل نمی‌کنیم.
        # بنابراین یک map جدید می‌سازیم: vector-id ترتیب افزایشی -> chunk_id مرتب‌شده بر اساس ترتیب اضافه‌شدن.
        self.id_to_chunk = {}
        for vid, ch_id in enumerate(chunk_ids):
            self.id_to_chunk[int(vid)] = int(ch_id)
        self._save_faiss()

        # BM25 fresh
        self._rebuild_bm25_from_db()
        self._save_bm25()
