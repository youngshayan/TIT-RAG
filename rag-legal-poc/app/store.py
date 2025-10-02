# app/store.py
from __future__ import annotations
from typing import Optional, List, Dict, Tuple, Any, Set
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

        # ------------- Chunk-level FAISS + mapping -------------
        self.index: Optional[faiss.Index] = None
        self.id_to_chunk: Dict[int, int] = {}
        self._load_faiss()
        self._ensure_idmap()

        # ------------- Doc-level FAISS + mapping (NEW) -------------
        self.doc_index: Optional[faiss.Index] = None
        self.doc_idmap: Dict[int, int] = {}
        self._load_doc_faiss()
        self._ensure_doc_idmap()

        # ------------- BM25 (chunk-level) -------------
        self.bm25: Optional[BM25Okapi] = None
        self.bm25_tokens: List[List[str]] = []
        self._load_bm25()

    # ---------------------- small utils ----------------------
    def _ensure_idmap(self):
        if self.index is None:
            return
        if not (isinstance(self.index, faiss.IndexIDMap) or isinstance(self.index, faiss.IndexIDMap2)):
            self.index = faiss.IndexIDMap(self.index)

    def _ensure_doc_idmap(self):
        if self.doc_index is None:
            return
        if not (isinstance(self.doc_index, faiss.IndexIDMap) or isinstance(self.doc_index, faiss.IndexIDMap2)):
            self.doc_index = faiss.IndexIDMap(self.doc_index)

    # ---------------------- Chunk FAISS ----------------------
    def _new_faiss(self):
        base = faiss.IndexFlatIP(self.dim)
        self.index = faiss.IndexIDMap(base)
        self.id_to_chunk = {}

    def _load_faiss(self):
        try:
            if config.FAISS_INDEX_PATH.exists() and config.FAISS_MAP_PATH.exists():
                idx = faiss.read_index(str(config.FAISS_INDEX_PATH))
                if not (isinstance(idx, faiss.IndexIDMap2) or isinstance(idx, faiss.IndexIDMap)):
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

    # ---------------------- Doc FAISS (NEW) ----------------------
    @property
    def _doc_index_path(self) -> Path:
        return getattr(config, "DOC_FAISS_INDEX_PATH", config.DATA_DIR / "faiss_doc.index")

    @property
    def _doc_map_path(self) -> Path:
        return getattr(config, "DOC_FAISS_MAP_PATH", config.DATA_DIR / "faiss_doc_map.json")

    def _new_doc_faiss(self):
        base = faiss.IndexFlatIP(self.dim)
        self.doc_index = faiss.IndexIDMap(base)
        self.doc_idmap = {}

    def _load_doc_faiss(self):
        p_idx = self._doc_index_path
        p_map = self._doc_map_path
        try:
            if p_idx.exists() and p_map.exists():
                idx = faiss.read_index(str(p_idx))
                if not (isinstance(idx, faiss.IndexIDMap2) or isinstance(idx, faiss.IndexIDMap)):
                    idx = faiss.IndexIDMap(idx)
                self.doc_index = idx
                self.doc_idmap = json.loads(p_map.read_text("utf-8"))
                self.doc_idmap = {int(k): int(v) for k, v in self.doc_idmap.items()}
            else:
                self._new_doc_faiss()
                self._save_doc_faiss()
        except Exception:
            self._new_doc_faiss()
            self._save_doc_faiss()

    def _save_doc_faiss(self):
        faiss.write_index(self.doc_index, str(self._doc_index_path))
        self._doc_map_path.write_text(
            json.dumps({int(k): int(v) for k, v in self.doc_idmap.items()}, ensure_ascii=False),
            encoding="utf-8"
        )

    def _reset_doc_faiss(self):
        self._new_doc_faiss()
        self._save_doc_faiss()

    def _init_doc_faiss(self, dim: int):
        base = faiss.IndexFlatIP(dim)
        self.doc_index = faiss.IndexIDMap(base)
        self.doc_idmap = {}

    # ---------------------- BM25 ----------------------
    def _tokenize(self, text) -> List[str]:
        if isinstance(text, dict):
            text = text.get("text", "")
        text = text or ""
        return re.findall(r"[\w\u0600-\u06FF]+", str(text))

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

    def _reset_bm25(self):
        self.bm25_tokens = []
        self.bm25 = None
        self._save_bm25()

    def _rebuild_bm25_from_db(self):
        with Session(self.engine) as s:
            stmt = select(Chunk).order_by(Chunk.id.asc())
            rows = list(s.exec(stmt))
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
    def _build_doc_repr(self, doc: Document, chunks: List[Chunk]) -> str:
        """
        نمایندهٔ متن سند برای Doc-level:
        عنوان + ۲ قطعهٔ اول + (در صورت وجود) بخش‌هایی از متادیتا.
        """
        title = (doc.title or "").strip()
        part1 = (chunks[0].text if chunks else "") or ""
        part2 = (chunks[1].text if len(chunks) > 1 else "") or ""
        try:
            meta = json.loads(doc.meta) if doc.meta else {}
        except Exception:
            meta = {}
        issuer = meta.get("issuer") or meta.get("source") or ""
        number = meta.get("number") or ""
        header = f"{title}\n{issuer} {number}".strip()
        raw = (header + "\n" + part1 + "\n" + part2).strip()
        return normalize_persian(raw)[:3000]  # کوتاه و کافی

    def index_doc(self, doc_id: int):

        chunks = self.get_doc_chunks(doc_id)
        if not chunks:
            return
        doc = self.get_document(doc_id)

        # ---- chunk-level embeddings ----
        texts = [normalize_persian(c.text or "") for c in chunks]
        passages = [f"passage: {t}" for t in texts]
        vec = self.model.encode(passages, normalize_embeddings=True, convert_to_numpy=True).astype("float32")

        start_id = len(self.id_to_chunk)
        ids = np.arange(start_id, start_id + vec.shape[0]).astype("int64")

        self.index.add_with_ids(vec, ids)
        for i, ch in enumerate(chunks):
            self.id_to_chunk[int(ids[i])] = int(ch.id)
        self._save_faiss()

        # ---- doc-level embedding (NEW) ----
        if doc:
            rep = self._build_doc_repr(doc, chunks)
            dvec = self.model.encode([f"document: {rep}"], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
            d_start = len(self.doc_idmap)
            dids = np.arange(d_start, d_start + 1).astype("int64")
            self.doc_index.add_with_ids(dvec, dids)
            self.doc_idmap[int(dids[0])] = int(doc.id)
            self._save_doc_faiss()

        # ---- BM25 (keep same ordering as vector-id) ----
        tokens_list = [self._tokenize(t) for t in texts]
        self.bm25_tokens.extend(tokens_list)
        self.bm25 = BM25Okapi(self.bm25_tokens)
        self._save_bm25()

    # ---------------------- Hybrid Search (with Doc prefilter) ----------------------
    def _prefilter_docs(self, qn: str, m: int = 12) -> set[int]:

        if self.doc_index is None or self.doc_index.ntotal == 0:
            return set()
        qv = self.model.encode([f"query: {qn}"], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
        scores, idxs = self.doc_index.search(qv, min(m, max(1, self.doc_index.ntotal)))
        picked: set[int] = set()
        for i in idxs[0]:
            if i == -1:
                continue
            did = self.doc_idmap.get(int(i))
            if did is not None:
                picked.add(did)
        return picked

    def search_hybrid(
        self,
        query: str,
        vec_k: int,
        bm25_k: int,
        restrict_doc_ids: Optional[Set[int]] = None,
        allow_broaden: bool = False,
    ) -> List[Tuple[int, float, str]]:

        def _run(vec_k_val: int, bm25_k_val: int, restrict: Optional[Set[int]]) -> List[Tuple[int, float, str]]:
            out: List[Tuple[int, float, str]] = []
            qn = normalize_persian(query or "")

            # ---- (1) Doc prefilter ----
            shortlist = self._prefilter_docs(qn, m=12)
            restrict_set = set(restrict) if restrict else set()
            # اگر هر دو وجود دارند، اشتراک بگیر
            if restrict_set and shortlist:
                shortlist = shortlist.intersection(restrict_set)
            elif restrict_set:
                shortlist = restrict_set

            restrict_active = len(shortlist) > 0

            # ---- (2) Vector (chunk-level) ----
            vec_hits = []
            if self.index is not None and self.index.ntotal > 0:
                qv = self.model.encode([f"query: {qn}"], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
                scores, idxs = self.index.search(qv, min(vec_k_val * 2, max(1, self.index.ntotal)))
                for i, s in zip(idxs[0], scores[0]):
                    if i == -1:
                        continue
                    cid = self.id_to_chunk.get(int(i))
                    if cid is None:
                        continue
                    if restrict_active:
                        doc = self.get_document_by_chunk(cid)
                        if (not doc) or (doc.id not in shortlist):
                            continue
                    vec_hits.append((cid, float(s), "vec"))

            # ---- (3) BM25 (chunk-level) ----
            bm_hits = []
            if self.bm25 and self.bm25_tokens:
                scores = self.bm25.get_scores(self._tokenize(qn))
                if len(scores):
                    k = min(bm25_k_val * 2, len(scores))
                    top_idx = np.argpartition(-scores, k - 1)[:k]
                    top_idx = top_idx[np.argsort(-scores[top_idx])]
                    ordered_ids = [cid for _, cid in sorted(self.id_to_chunk.items(), key=lambda x: x[0])]
                    for bi in top_idx:
                        if 0 <= bi < len(ordered_ids):
                            cid = ordered_ids[bi]
                            if restrict_active:
                                doc = self.get_document_by_chunk(cid)
                                if (not doc) or (doc.id not in shortlist):
                                    continue
                            bm_hits.append((cid, float(scores[bi]), "bm25"))

            # ---- merge ----
            merged: Dict[int, Tuple[float, str]] = {}
            for cid, sc, tag in bm_hits + vec_hits:
                if cid not in merged or sc > merged[cid][0]:
                    merged[cid] = (sc, tag)

            out2 = sorted([(cid, sc, tag) for cid, (sc, tag) in merged.items()],
                          key=lambda x: -x[1])
            return out2


        first = _run(vec_k, bm25_k, restrict_doc_ids)
        if first or not allow_broaden:
            return first[: max(vec_k, bm25_k)]

        widened = _run(vec_k, bm25_k, restrict=None)
        return widened[: max(vec_k, bm25_k)]

    # ---------------------- Compatibility shim ----------------------
    def add_document(self, title: str, source_path, full_text: str = "", meta: dict | None = None) -> int:
        from app.ingest import _build_chunks, _load_text_from_path

        spath = Path(source_path) if source_path is not None else None
        if not full_text and spath and spath.exists():
            full_text = _load_text_from_path(spath)

        chunks = _build_chunks(full_text or "")
        doc_id = self.add_document_with_chunks(title or (spath.stem if spath else "Untitled"), spath, chunks, full_text or "")
        self.index_doc(doc_id)
        return doc_id

    # ---------------------- Re-embed all (fresh build) ----------------------
    def rebuild_all_indexes_from_db(self, text_prefix: str = "passage: ", normalize_fn=None):

        with Session(self.engine) as s:
            stmt = select(Chunk.id, Chunk.text, Chunk.doc_id).order_by(Chunk.id.asc())
            rows = list(s.exec(stmt))
            docs_stmt = select(Document).order_by(Document.id.asc())
            docs = list(s.exec(docs_stmt))
        if not rows:

            self._reset_faiss()
            self._reset_doc_faiss()
            self._reset_bm25()
            return

        # --- Chunk-level
        chunk_texts: List[str] = []
        chunk_ids: List[int] = []
        docid_to_chunks: Dict[int, List[int]] = {}
        for cid, t, did in rows:
            t2 = normalize_fn(t) if normalize_fn else (t or "")
            chunk_texts.append(f"{text_prefix}{t2}")
            chunk_ids.append(int(cid))
            docid_to_chunks.setdefault(int(did), []).append(int(cid))

        # encode in batches
        batch = 256
        vecs = []
        for i in range(0, len(chunk_texts), batch):
            part = self.model.encode(chunk_texts[i:i+batch], normalize_embeddings=True, convert_to_numpy=True)
            vecs.append(part)
        mat = np.vstack(vecs).astype("float32")

        # reset & add
        self._reset_faiss()
        self._init_faiss(dim=mat.shape[1])
        self.index.add(mat)
        # mapِ vector-id -> chunk_id
        self.id_to_chunk = {int(vid): int(chid) for vid, chid in enumerate(chunk_ids)}
        self._save_faiss()

        # --- Doc-level
        self._reset_doc_faiss()
        self._init_doc_faiss(dim=self.dim)
        doc_vecs = []
        doc_ids = []
        for d in docs:

            first_two_texts: List[str] = []
            for cid in docid_to_chunks.get(d.id, [])[:2]:
                ct = next((t for (ccid, t, _did) in rows if ccid == cid), "")
                first_two_texts.append(ct or "")
            fake_chunks = [
                Chunk(id=0, doc_id=d.id, position=0, text=first_two_texts[0] if len(first_two_texts) > 0 else ""),
                Chunk(id=0, doc_id=d.id, position=1, text=first_two_texts[1] if len(first_two_texts) > 1 else ""),
            ]
            rep = self._build_doc_repr(d, fake_chunks)
            doc_ids.append(int(d.id))
            doc_vecs.append(rep)
        if doc_vecs:
            doc_emb = []
            for i in range(0, len(doc_vecs), batch):
                part = self.model.encode([f"document: {normalize_persian(x)}" for x in doc_vecs[i:i+batch]],
                                         normalize_embeddings=True, convert_to_numpy=True)
                doc_emb.append(part)
            dmat = np.vstack(doc_emb).astype("float32")
            self.doc_index.add(dmat)
            self.doc_idmap = {int(vid): int(did) for vid, did in enumerate(doc_ids)}
            self._save_doc_faiss()

        # --- BM25 fresh
        self._rebuild_bm25_from_db()
        self._save_bm25()

    # ---------------------- Nuclear reset (wipe all) ----------------------
    def reset_all(self):

        # drop tables
        try:
            SQLModel.metadata.drop_all(self.engine)
        except Exception:
            pass
        SQLModel.metadata.create_all(self.engine)

        # delete index files
        for p in [
            config.FAISS_INDEX_PATH, config.FAISS_MAP_PATH, config.BM25_CORPUS_PATH,
            getattr(config, "DOC_FAISS_INDEX_PATH", config.DATA_DIR / "faiss_doc.index"),
            getattr(config, "DOC_FAISS_MAP_PATH",   config.DATA_DIR / "faiss_doc_map.json"),
        ]:
            try:
                Path(p).unlink(missing_ok=True)
            except Exception:
                pass

        # re-init in-memory structures
        self._reset_faiss()
        self._reset_doc_faiss()
        self._reset_bm25()
