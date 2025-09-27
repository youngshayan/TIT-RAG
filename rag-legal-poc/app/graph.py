# app/graph.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Iterable
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from app.store import Store

# ---------------------------
# تنظیمات
# ---------------------------

_MIN_TOKEN_LEN = 3
_TOP_KEYWORDS_PER_PAIR = 6        # چند کلیدواژه مشترک برای یال‌ها
_NODE_LABEL_WORDS = 3             # حداکثر تعداد کلمات در لیبل نودها (query/chunk/doc)

# ---------------------------
# ابزار وزن‌دهی
# ---------------------------

def _minmax_scale(values: Iterable[float], lo: float = 0.2, hi: float = 1.0) -> List[float]:
    vals = list(values)
    if not vals:
        return []
    vmin = min(vals); vmax = max(vals)
    if math.isclose(vmax, vmin):
        mid = (lo + hi) / 2.0
        return [mid for _ in vals]
    out = []
    for v in vals:
        x = (v - vmin) / (vmax - vmin)
        out.append(lo + x * (hi - lo))
    return out

# ---------------------------
# توکن‌سازی و کلیدواژه
# ---------------------------

_FA_STOP = {
    "و","یا","از","با","برای","به","در","که","را","این","آن","می","شود","شده","شد","ها","های","تا","بر","بین","برابر",
    "نیز","هم","اما","اگر","هر","نه","بود","باشد","گردد","گردیده","پس","ضمن","بدون","طبق","پس‌از",
}
_EN_STOP = {
    "the","a","an","and","or","to","of","in","on","for","at","by","is","are","was","were","be","been","being",
    "this","that","these","those","as","with","from","it","its","into","over","under","no","not","but","if",
}

_TOKEN_RX = re.compile(r"[\w\u0600-\u06FF]+")

def _tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    return _TOKEN_RX.findall(text)

def _is_good_token(tok: str) -> bool:
    if len(tok) < _MIN_TOKEN_LEN: return False
    if tok in _FA_STOP or tok in _EN_STOP: return False
    if tok.isdigit(): return False
    return True

def _top_keywords(text: str, n: int) -> List[str]:
    toks = [t for t in _tokenize(text) if _is_good_token(t)]
    if not toks: return []
    c = Counter(toks)
    return [w for w, _ in c.most_common(n)]

def _extract_pair_keywords(query: str, chunk: str, top_n: int = _TOP_KEYWORDS_PER_PAIR) -> List[Tuple[str, float]]:
    q_toks = [t for t in _tokenize(query) if _is_good_token(t)]
    c_toks = [t for t in _tokenize(chunk) if _is_good_token(t)]
    if not q_toks or not c_toks: return []
    cq = Counter(q_toks); cc = Counter(c_toks)
    q_max = max(cq.values()); c_max = max(cc.values())
    commons = set(cq) & set(cc)
    scored: List[Tuple[str, float]] = []
    for w in commons:
        sq = cq[w] / q_max
        sc = cc[w] / c_max
        scored.append((w, 0.5 * sq + 0.5 * sc))
    scored.sort(key=lambda x: -x[1])
    return scored[:top_n]

def _short_label_from_keywords(text: str, n_words: int) -> str:
    """
    از متن کلیدواژه‌های برتر را می‌گیرد و با فاصله نشان می‌دهد؛
    اگر چیزی نبود، از اول متن تا حداکثر ~40 کاراکتر را برمی‌گرداند.
    """
    kws = _top_keywords(text, n_words)
    if kws:
        return " ".join(kws)
    # fallback خیلی کوتاه
    s = (text or "").strip().replace("\n", " ")
    return (s[:40] + "…") if len(s) > 40 else s

def _short_label_for_doc(title: str, source_path: str, n_words: int) -> str:
    base = title or Path(source_path or "").name or "Doc"
    # اگر تایتل طولانی بود، با کلیدواژه خلاصه کنیم
    kw = _short_label_from_keywords(base, n_words)
    return kw or (base[:40] + "…" if len(base) > 40 else base)

# ---------------------------
# سازه‌های گراف
# ---------------------------

from dataclasses import dataclass

@dataclass
class GraphNode:
    id: str
    label: str
    type: str  # "query" | "chunk" | "doc" | "keyword"
    score: float = 0.5
    classes: str = ""

    def to_cy(self) -> Dict[str, Any]:
        cls = self.classes or self.type
        return {"data": {"id": self.id, "label": self.label, "type": self.type, "score": float(self.score)}, "classes": cls}

@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    weight: float = 0.5
    label: str = ""
    classes: str = ""

    def to_cy(self) -> Dict[str, Any]:
        data = {"id": self.id, "source": self.source, "target": self.target, "weight": float(self.weight)}
        if self.label:
            data["label"] = self.label
        return {"data": data, "classes": self.classes or ""}

# ---------------------------
# ساخت گراف Cytoscape
# ---------------------------

def build_answer_graph(
    query: str,
    ranked_candidates: List[Tuple[int, float, str]],  # [(chunk_id, score, tag)]
    store: Store,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    گراف کوتاه‌نویس:
    - لیبل Query/Chunk/Doc فقط ۲–۳ واژه‌ی کلیدی (قابل تنظیم با _NODE_LABEL_WORDS)
    - یال‌ها و وزن‌ها مانند نسخه‌ی قبل (semantic/match/ref) با نرمال‌سازی
    """
    ranked = ranked_candidates[: top_k if top_k and top_k > 0 else len(ranked_candidates)]

    nodes: Dict[str, GraphNode] = {}
    edges: List[GraphEdge] = []

    # 1) Query node: 2–3 کلیدواژه اصلی پرسش
    q_label = _short_label_from_keywords(query, _NODE_LABEL_WORDS) or (query[:40] + "…" if len(query) > 40 else query)
    nodes["q"] = GraphNode(id="q", label=q_label, type="query", score=1.0, classes="query")

    # 2) Chunk & Doc nodes
    chunk_nodes: List[GraphNode] = []
    doc_nodes_map: Dict[int, GraphNode] = {}
    chunk_sem_scores: Dict[str, float] = {}
    max_sc = max([sc for (_cid, sc, _t) in ranked], default=1.0)

    for cid, sc, tag in ranked:
        ch = store.get_chunk(cid)
        if not ch:
            continue
        doc = store.get_document(ch.doc_id)

        # Chunk node label: 2–3 واژه مشترک با query؛ اگر نبود، 2–3 کلیدواژه‌ی خود chunk
        chunk_text = (ch.text or "")
        pair_kws = [w for (w, _s) in _extract_pair_keywords(query, chunk_text, top_n=_TOP_KEYWORDS_PER_PAIR)]
        if pair_kws:
            ch_label = " ".join(pair_kws[:_NODE_LABEL_WORDS])
        else:
            ch_label = _short_label_from_keywords(chunk_text, _NODE_LABEL_WORDS)

        ch_id = f"c{cid}"
        ch_score = float(sc / max_sc) if max_sc > 0 else 0.6
        chunk_node = GraphNode(id=ch_id, label=ch_label or f"chunk {cid}", type="chunk", score=ch_score, classes="chunk")
        nodes[ch_id] = chunk_node
        chunk_nodes.append(chunk_node)
        chunk_sem_scores[ch_id] = ch_score

        # Doc node label: 2–3 واژه از title یا نام فایل
        if doc and doc.id not in doc_nodes_map:
            doc_label = _short_label_for_doc(doc.title or "", doc.source_path or "", _NODE_LABEL_WORDS)
            doc_nodes_map[doc.id] = GraphNode(
                id=f"d{doc.id}",
                label=doc_label,
                type="doc",
                score=0.7,
                classes="doc",
            )

    for dn in doc_nodes_map.values():
        nodes[dn.id] = dn

    # 3) Edges: query→chunk (semantic)
    sem_edges_raw: List[Tuple[str, float]] = []
    for cn in chunk_nodes:
        w = chunk_sem_scores.get(cn.id, 0.5)
        sem_edges_raw.append((f"q->{cn.id}", w))
    sem_scaled = _minmax_scale([w for (_eid, w) in sem_edges_raw], lo=0.25, hi=0.95)
    for (eid, _), w in zip(sem_edges_raw, sem_scaled):
        src, tgt = "q", eid.split("->")[1]
        edges.append(GraphEdge(id=f"e_{src}_{tgt}_sem", source=src, target=tgt, weight=w, label="semantic", classes="semantic"))

    # 4) Keywords nodes (global unique) + match edges
    kw_global_scores: Dict[str, float] = defaultdict(float)
    kw_edges_q: List[Tuple[str, float]] = []
    kw_edges_c: List[Tuple[str, float]] = []
    kw_nodes_seen: Dict[str, GraphNode] = {}

    for cn in chunk_nodes:
        chunk_id_int = int(cn.id[1:])
        ch = store.get_chunk(chunk_id_int)
        ctext = (ch.text or "") if ch else ""
        kws = _extract_pair_keywords(query, ctext, top_n=_TOP_KEYWORDS_PER_PAIR)
        for term, score in kws:
            kid = f"k_{term}"
            if kid not in kw_nodes_seen:
                kw_nodes_seen[kid] = GraphNode(id=kid, label=term, type="keyword", score=0.6, classes="keyword")
                nodes[kid] = kw_nodes_seen[kid]
            kw_global_scores[kid] += score
            kw_edges_q.append((f"e_q_{kid}_match", score))
            kw_edges_c.append((f"e_{kid}_{cn.id}_match", score))

    q_scaled = _minmax_scale([w for (_eid, w) in kw_edges_q], lo=0.25, hi=0.9)
    for (eid, _), w in zip(kw_edges_q, q_scaled):
        # e_q_k_term_match → src=q, tgt=k_term
        if eid.endswith("_match"):
            body = eid[len("e_q_") : -len("_match")]  # k_term
            src, tgt = "q", body
        else:
            src = tgt = "q"
        edges.append(GraphEdge(id=eid, source=src, target=tgt, weight=w, label="keyword", classes="match"))

    c_scaled = _minmax_scale([w for (_eid, w) in kw_edges_c], lo=0.25, hi=0.9)
    for (eid, _), w in zip(kw_edges_c, c_scaled):
        # e_k_term_c{cid}_match → src=k_term, tgt=c{cid}
        if eid.endswith("_match"):
            body = eid[len("e_") : -len("_match")]  # k_term_c{cid}
            # آخرین "_c" را پیدا کنیم
            under = body.rfind("_c")
            if under > 0:
                src = body[:under]      # k_term
                tgt = body[under + 1:]  # c{cid}
            else:
                src = tgt = "q"
        else:
            src = tgt = "q"
        edges.append(GraphEdge(id=eid, source=src, target=tgt, weight=w, label="keyword", classes="match"))

    # اندازه‌ی نودهای keyword بر اساس امتیاز تجمیعی
    if kw_global_scores:
        scaled_kw = _minmax_scale(list(kw_global_scores.values()), lo=0.45, hi=0.95)
        for (kid, _), s in zip(kw_global_scores.items(), scaled_kw):
            if kid in nodes:
                nodes[kid].score = max(nodes[kid].score, s)

    # 5) Edges: chunk→doc (ref)
    ref_raw: List[Tuple[str, float]] = []
    for cn in chunk_nodes:
        chunk_id_int = int(cn.id[1:])
        ch = store.get_chunk(chunk_id_int)
        if not ch: continue
        did = f"d{ch.doc_id}"
        if did not in nodes: continue
        ref_raw.append((f"e_{cn.id}_{did}_ref", cn.score))
    ref_scaled = _minmax_scale([w for (_eid, w) in ref_raw], lo=0.25, hi=0.85)
    for (eid, _), w in zip(ref_raw, ref_scaled):
        if eid.endswith("_ref"):
            body = eid[len("e_") : -len("_ref")]
            under = body.find("_d")
            if under > 0:
                src = body[:under]
                tgt = body[under + 1:]
            else:
                src = tgt = "q"
        else:
            src = tgt = "q"
        edges.append(GraphEdge(id=eid, source=src, target=tgt, weight=w, label="ref", classes="ref"))

    # خروجی Cytoscape
    elements = [n.to_cy() for n in nodes.values()] + [e.to_cy() for e in edges]
    return {
        "nodes": [n.to_cy() for n in nodes.values()],
        "edges": [e.to_cy() for e in edges],
        "elements": elements,
    }
