# app/graph.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
import re
import math
import json
from pathlib import Path

from app.store import Store

# -----------------------------
# Utilities
# -----------------------------

_FA_STOPWORDS = {
    "از","با","به","در","و","را","که","برای","یا","تا","این","آن","بین","بر","طبق","طبقِ",
    "می","های","خواهند","خواهد","کرد","شود","شده","بود","بودن","نیست","است","هست","هم","اما",
    "همچنین","بنابراین","باید","نباید","اگر","اگرچه","مثل","مانند","کلیه","کلاً","کل","هر","هیچ",
    "پس","قبل","بعد","ضمن","بدون","برابر","مطابق","موضوع","تبصره","ماده","مواد","پیوست","پیوست‌ها",
    "صرفاً","صرفا","حداکثر","حداقل","اعم","غیر","تمامی","کلیهٔ","آن‌ها","آنها","ایشان",
}
_EN_STOPWORDS = {
    "a","an","the","and","or","but","for","to","of","in","on","at","by","from","with","as",
    "is","are","was","were","be","been","being","this","that","these","those","it","its","their","there",
    "can","could","should","would","may","might","must","shall","will","do","does","did",
}
STOPWORDS = _FA_STOPWORDS.union(_EN_STOPWORDS)

TOKEN_RE = re.compile(r"[0-9A-Za-z\u0600-\u06FF]+", re.UNICODE)

def _tokens(text: str) -> List[str]:
    if not text:
        return []
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) >= 2]

def _top_keywords(text: str, max_kw: int = 8) -> List[str]:
    toks = _tokens(text)
    if not toks:
        return []
    # unigram
    freq: Dict[str, int] = {}
    for t in toks:
        freq[t] = freq.get(t, 0) + 1
    # bigram
    big: Dict[str, int] = {}
    for i in range(len(toks) - 1):
        a, b = toks[i], toks[i + 1]
        if a in STOPWORDS or b in STOPWORDS:
            continue
        bg = f"{a} {b}"
        big[bg] = big.get(bg, 0) + 1
    # score
    scores: Dict[str, float] = {}
    for w, c in freq.items():
        scores[w] = c * 1.0
    for bg, c in big.items():
        scores[bg] = scores.get(bg, 0) + c * 1.6
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    kw = [w for (w, _s) in ranked[: max_kw * 2]]
    cleaned: List[str] = []
    for w in kw:
        if len(w) <= 28 and (1 <= len(w.split()) <= 3):
            cleaned.append(w)
        if len(cleaned) >= max_kw:
            break
    return cleaned

def _short_label_from_text(text: str, fallback: str = "") -> str:
    kws = _top_keywords(text, max_kw=3)
    if kws:
        return " • ".join(kws[:3])
    text = (text or "").strip()
    if not text:
        return fallback or "—"
    toks = _tokens(text)
    if not toks:
        return (text[:22] + "…") if len(text) > 22 else text
    short = " ".join(toks[:3])
    return short[:28] + ("…" if len(short) > 28 else "")

def _clip_preview(text: str, n=200) -> str:
    s = (text or "").strip().replace("\n", " ")
    return (s[:n] + "…") if len(s) > n else s

def _normalize(values: List[float]) -> Dict[int, float]:
    if not values:
        return {}
    vmin, vmax = min(values), max(values)
    if math.isclose(vmin, vmax):
        return {i: 1.0 for i in range(len(values))}
    rng = (vmax - vmin) or 1.0
    return {i: (v - vmin) / rng for i, v in enumerate(values)}

# --- filename helpers (wrap-able) ---
_ZWSP = "\u200b"
def _wrapable_filename(name: str) -> str:
    s = name or ""
    if not s:
        return s
    s = re.sub(r"([_\-\.\/\\])", r"\1" + _ZWSP, s)   # break after separators
    if " " not in s and len(s) > 18:
        parts = [s[i:i+8] for i in range(0, len(s), 8)]
        s = _ZWSP.join(parts)
    return s

def _doc_filename_label(doc, meta: Dict[str, Any]) -> str:
    name = ""
    try:
        if meta and isinstance(meta, dict):
            name = (meta.get("filename") or "").strip()
    except Exception:
        name = ""
    if not name:
        sp = (getattr(doc, "source_path", "") or "").strip()
        if sp:
            name = Path(sp).name
    if not name:
        name = (getattr(doc, "title", "") or "").strip() or f"doc-{getattr(doc, 'id', '')}"
    # remove extension
    if "." in name:
        base = ".".join(name.split(".")[:-1])
        name = base or name
    return _wrapable_filename(name)

# -----------------------------
# Graph elements
# -----------------------------

@dataclass
class GraphNode:
    id: str
    label: str
    type: str  # query | keyword | chunk | doc
    score: float = 0.0
    classes: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)  # <<— برای داده‌های بیشتر

    def to_cy(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "score": float(max(0.0, min(1.0, self.score))),
        }
        data.update(self.extra or {})
        return {"data": data, "classes": self.classes or self.type}

@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    etype: str  # semantic | match | ref
    weight: float = 0.0
    label: str = ""

    def to_cy(self) -> Dict[str, Any]:
        d = {
            "data": {
                "id": self.id,
                "source": self.source,
                "target": self.target,
                "weight": float(max(0.0, min(1.0, self.weight))),
                "etype": self.etype,
            },
            "classes": self.etype,
        }
        if self.label:
            d["data"]["label"] = self.label
        return d

# -----------------------------
# Main builder
# -----------------------------

def build_answer_graph(
    query: str,
    reranked: List[Tuple[int, float, str]],
    store: Store,
    top_k: int = 5,
) -> Dict[str, Any]:
    elements: List[Dict[str, Any]] = []
    edges: List[GraphEdge] = []
    nodes: Dict[str, GraphNode] = {}

    # Query
    q_label = _short_label_from_text(query, fallback="Query")
    q_node = GraphNode(id="q", label=q_label, type="query", score=1.0, classes="query")
    nodes[q_node.id] = q_node

    top = reranked[: max(1, top_k)]
    if not top:
        return {"elements": [q_node.to_cy()], "kpis": {"sources": 0, "keywordCoverage": 0.0, "confidence": 0.0}}

    raw_scores = [float(sc) for (_cid, sc, _tag) in top]
    idx2norm = _normalize(raw_scores)
    doc_ids_used = set()
    chunk_nodes_order: List[str] = []

    for i, (cid, sc, _tag) in enumerate(top):
        ch = store.get_chunk(cid)
        if not ch:
            continue
        doc = store.get_document(ch.doc_id)

        ch_label = _short_label_from_text(ch.text or "", fallback=f"CH-{cid}")
        ch_score = idx2norm.get(i, 0.5)
        ch_id = f"ch_{cid}"
        nodes[ch_id] = GraphNode(
            id=ch_id, label=ch_label, type="chunk", score=ch_score, classes="chunk",
            extra={"preview": _clip_preview(ch.text or "", 220), "score": round(float(sc), 4)}
        )
        chunk_nodes_order.append(ch_id)

        edges.append(GraphEdge(id=f"e_sem_{cid}", source="q", target=ch_id, etype="semantic", weight=ch_score, label="semantic"))

        meta: Dict[str, Any] = {}
        if doc:
            if doc.id not in doc_ids_used:
                doc_ids_used.add(doc.id)
            if doc.meta and isinstance(doc.meta, str):
                try:
                    meta = json.loads(doc.meta)
                except Exception:
                    meta = {}

            doc_id = f"doc_{doc.id}"
            if doc_id not in nodes:
                doc_label = _doc_filename_label(doc, meta)
                nodes[doc_id] = GraphNode(
                    id=doc_id, label=doc_label, type="doc", score=0.8, classes="doc",
                    extra={
                        "filename": doc_label,
                        "docTitle": (doc.title or ""),
                        "sourcePath": (doc.source_path or ""),
                        "meta": meta,
                    }
                )
            edges.append(GraphEdge(id=f"e_ref_{cid}_{doc.id}", source=ch_id, target=doc_id, etype="ref", weight=1.0, label="ref"))

            # همچنین chunk را به همان اطلاعات سند غنی کنیم (برای پنل جزئیات)
            nodes[ch_id].extra.update({
                "docId": doc.id,
                "docTitle": (doc.title or ""),
                "sourcePath": (doc.source_path or ""),
                "meta": meta,
                "filename": _doc_filename_label(doc, meta),
            })

    # push chunk/doc nodes
    for nid, n in list(nodes.items()):
        if n.type in ("chunk", "doc"):
            elements.append(n.to_cy())

    # keywords
    q_keywords = _top_keywords(query, max_kw=6)
    covered = 0
    for kw in q_keywords:
        kid = f"k_{kw}"
        if kid not in nodes:
            nodes[kid] = GraphNode(id=kid, label=kw, type="keyword", score=0.6, classes="keyword")
            elements.append(nodes[kid].to_cy())
        w_qk = min(1.0, max(0.15, len(kw) / 12.0))
        edges.append(GraphEdge(id=f"e_qk_{kw}", source="q", target=kid, etype="match", weight=w_qk, label="match"))
        connected = False
        kwtoks = set(_tokens(kw))
        for ch_id in chunk_nodes_order:
            ltoks = set(_tokens(nodes[ch_id].label))
            inter = kwtoks.intersection(ltoks)
            if not inter:
                continue
            w_kc = min(1.0, max(0.1, len(inter) / max(1, len(kwtoks))))
            edges.append(GraphEdge(id=f"e_kc_{kw}_{ch_id}", source=kid, target=ch_id, etype="match", weight=w_kc, label="match"))
            connected = True
        if connected:
            covered += 1

    # normalize edge weights and push
    if edges:
        ws = [e.weight for e in edges]
        vmin, vmax = min(ws), max(ws)
        rng = (vmax - vmin) or 1.0
        for e in edges:
            e.weight = 0.15 + 0.85 * ((e.weight - vmin) / rng)
    for e in edges:
        elements.append(e.to_cy())

    kpis = {
        "sources": len(doc_ids_used),
        "keywordCoverage": (covered / max(1, len(q_keywords))) if q_keywords else 0.0,
        "confidence": sum(sorted([idx2norm.get(i, 0.0) for i in range(len(raw_scores))], reverse=True)[:3]) / max(1, min(3, len(raw_scores))),
    }

    qn = q_node.to_cy()
    qn["data"]["preview"] = _clip_preview(query, 220)
    qn["data"]["score"] = 1.0
    elements.append(qn)

    return {"elements": elements, "kpis": kpis}
