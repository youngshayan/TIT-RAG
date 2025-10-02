import React, { useMemo, useState } from "react";
import { ask, ChatTurn } from "../api";
import { toast } from "sonner";
import Markdown from "./Markdown";
import GraphView from "./GraphView";


class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { err: any }> {
  constructor(props: any) {
    super(props);
    this.state = { err: null };
  }
  static getDerivedStateFromError(error: any) {
    return { err: error };
  }
  componentDidCatch(error: any, info: any) {
    console.error("[UI] ErrorBoundary:", error, info);
  }
  render() {
    if (this.state.err) {
      return (
        <div className="p-4 border border-border rounded-xl bg-card-2 text-red-300">
          <div className="font-semibold mb-1">✖ خطا در نمایش محتوا</div>
          <div className="text-sm text-muted">جزئیات خطا در کنسول مرورگر ثبت شد.</div>
        </div>
      );
    }
    return this.props.children as any;
  }
}

// ---- Types ----
type Msg = { role: "user" | "assistant"; content: string; ts: number };

type CytoscapeElement = {
  data: Record<string, any>;
  group?: "nodes" | "edges";
  classes?: string;
};

type BackendGraph =
  | {
      elements?: any[];
      nodes?: any[];
      edges?: any[];
      keywords?: any[];
      kpis?: { sources?: number; keywordCoverage?: number; confidence?: number };
    }
  | null
  | undefined;

// ---- Helpers ----
const toStr = (v: any) => (v === undefined || v === null ? "" : String(v));

function shortenLabel(label: any, maxChars = 18): string {
  const s = toStr(label).trim();
  if (!s) return "";
  const clean = s.replace(/\s+/g, " ");
  return clean.length > maxChars ? clean.slice(0, maxChars - 1) + "…" : clean;
}

function isValidNodeLike(x: any) {
  const id = toStr(x?.id || x?.data?.id || x?.key || x?.node_id);
  return !!id;
}
function isValidEdgeLike(x: any) {
  const src = toStr(x?.source || x?.data?.source);
  const tgt = toStr(x?.target || x?.data?.target);
  return !!(src && tgt);
}

function buildElementsFromNodesEdges(g: any): CytoscapeElement[] {
  const out: CytoscapeElement[] = [];
  const nodesRaw: any[] = Array.isArray(g?.nodes) ? g.nodes : [];
  const edgesRaw: any[] = Array.isArray(g?.edges) ? g.edges : [];
  const kwsRaw: any[] = Array.isArray(g?.keywords) ? g.keywords : [];

  for (const n of [...nodesRaw, ...kwsRaw]) {
    if (!isValidNodeLike(n)) continue;
    const id = toStr(n.id || n?.data?.id || n.key || n.node_id);
    const rawLabel =
      n.label ?? n.title ?? n.text ?? n.name ?? n.keyword ?? n?.data?.label ?? n?.data?.title;
    const label = shortenLabel(rawLabel ?? id);
    const rawScore = Number(n.score ?? n.weight ?? n?.data?.score ?? 0);
    const score = isFinite(rawScore) ? Math.max(0, Math.min(1, rawScore > 1 ? rawScore / 100 : rawScore)) : 0;

    out.push({
      group: "nodes",
      data: {
        id,
        label,
        score,
        kind: n.kind || n.type || n.node_type || n?.data?.kind || "node",
        title: shortenLabel(n.title || n?.data?.title || label, 24),
      },
      classes: n.kind === "keyword" || n.type === "keyword" ? "keyword" : undefined,
    });
  }

  let i = 0;
  for (const e of edgesRaw) {
    if (!isValidEdgeLike(e)) continue;
    const source = toStr(e.source || e?.data?.source);
    const target = toStr(e.target || e?.data?.target);

    const rawW = Number(e.weight ?? e.score ?? e?.data?.weight ?? e?.data?.score ?? 0);
    const weight = isFinite(rawW) ? Math.max(0, Math.min(1, rawW > 1 ? rawW / 100 : rawW)) : 0.1;
    const label = shortenLabel(e.label ?? e.relation ?? e?.data?.label ?? "");

    out.push({
      group: "edges",
      data: {
        id: e.id ? toStr(e.id) : `${source}__${target}__${i++}`,
        source,
        target,
        weight,
        label,
      },
    });
  }

  return out;
}

function sanitizeElements(elList: any[]): CytoscapeElement[] {
  const nodes: CytoscapeElement[] = [];
  const edges: CytoscapeElement[] = [];

  for (const el of elList || []) {
    if (!el || !el.data) continue;
    if (!el.group) {
      el.group = el?.data?.source && el?.data?.target ? "edges" : "nodes";
    }

    // normalize node
    if (el.group === "nodes") {
      const id = toStr(el.data.id);
      if (!id) continue;
      el.data.id = id;
      const lab = el.data.label ?? el.data.title ?? id;
      el.data.label = shortenLabel(lab);
      const s0 = Number(el.data.score ?? 0);
      el.data.score = isFinite(s0) ? Math.max(0, Math.min(1, s0)) : 0;
      nodes.push(el);
      continue;
    }

    // normalize edge
    if (el.group === "edges") {
      const src = toStr(el.data.source);
      const tgt = toStr(el.data.target);
      if (!src || !tgt) continue;
      el.data.source = src;
      el.data.target = tgt;
      if (!el.data.id) el.data.id = `${src}__${tgt}`;
      const w0 = Number(el.data.weight ?? 0.1);
      el.data.weight = isFinite(w0) ? Math.max(0, Math.min(1, w0)) : 0.1;
      if (el.data.label) el.data.label = shortenLabel(el.data.label, 20);
      edges.push(el);
    }
  }

  const nodeIds = new Set(nodes.map((n) => n.data.id));
  const filteredEdges = edges.filter((e) => nodeIds.has(e.data.source) && nodeIds.has(e.data.target));

  return [...nodes, ...filteredEdges];
}

function normalizeGraph(g: BackendGraph): { elements: CytoscapeElement[]; kpis: any } {
  const empty = { elements: [] as CytoscapeElement[], kpis: {} as any };
  if (!g || typeof g !== "object") return empty;

  const kpis =
    (g as any).kpis && typeof (g as any).kpis === "object"
      ? (g as any).kpis
      : { sources: 0, keywordCoverage: 0, confidence: 0 };

  if (Array.isArray((g as any).elements)) {
    return { elements: sanitizeElements((g as any).elements), kpis };
  }

  const built = buildElementsFromNodesEdges(g);
  return { elements: sanitizeElements(built), kpis };
}

function persistHistory(question: string, answer: any) {
  try {
    const hist = JSON.parse(localStorage.getItem("chat_hist") || "[]");
    hist.unshift({
      q: question,
      a: answer?.answer ?? "",
      citations: answer?.citations ?? [],
      graph: answer?.graph ?? null,
      ts: Date.now(),
    });
    localStorage.setItem("chat_hist", JSON.stringify(hist.slice(0, 100)));
  } catch {}
}

export default function ChatPanel() {
  const [q, setQ] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [topK, setTopK] = useState<number>(5);
  const [lastGraph, setLastGraph] = useState<{ elements: CytoscapeElement[]; kpis: any } | null>(null);

  const onAsk = async () => {
    const text = q.trim();
    if (!text) {
      toast.warning("سؤال را وارد کنید.");
      return;
    }

    const newMsgs = [...msgs, { role: "user", content: text, ts: Date.now() }];
    setMsgs(newMsgs);
    setQ("");
    setBusy(true);
    setLastGraph(null);

    const historyForBackend: ChatTurn[] = newMsgs
      .slice(-3)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const data = await ask(text, topK, historyForBackend);

      const assistantText =
        data && typeof data.answer === "string" && data.answer.trim()
          ? data.answer.trim()
          : "پاسخی از مدل دریافت نشد.";

      const safeGraph = normalizeGraph(data?.graph);

      const withAssistant = [
        ...newMsgs,
        { role: "assistant", content: assistantText, ts: Date.now() },
      ];
      setMsgs(withAssistant);

      if (safeGraph.elements.length > 0) setLastGraph(safeGraph);
      else setLastGraph(null);

      (window as any).__debugLastGraph = safeGraph;

      persistHistory(text, data);
    } catch (e: any) {
      console.error("[ChatPanel] ask error:", e);
      toast.error(e?.message || "خطا در پرسش");
      setLastGraph(null);
    } finally {
      setBusy(false);
    }
  };

  const GraphCard = useMemo(() => {
    if (!lastGraph || !Array.isArray(lastGraph.elements) || lastGraph.elements.length === 0) {
      return null;
    }
    return (
      <ErrorBoundary>
        <div className="mt-4 border border-border rounded-2xl p-4 bg-card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">نقشهٔ استدلال پاسخ</h3>
            <div className="text-xs text-muted">
              منابع: {lastGraph.kpis?.sources ?? 0} • پوشش کلیدواژه:{" "}
              {typeof lastGraph.kpis?.keywordCoverage === "number"
                ? `${Math.round(lastGraph.kpis.keywordCoverage * 100)}%`
                : "—"}{" "}
              • اطمینان:{" "}
              {typeof lastGraph.kpis?.confidence === "number"
                ? `${Math.round(lastGraph.kpis.confidence * 100)}%`
                : "—"}
            </div>
          </div>
          <GraphView data={lastGraph as any} height={360} />
        </div>
      </ErrorBoundary>
    );
  }, [lastGraph]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* پرسش */}
      <div className="bg-card rounded-2xl shadow-card p-6 lg:col-span-1 border border-border">
        <h2 className="text-lg font-semibold mb-4">🔎 پرسش</h2>
        <textarea
          className="textarea h-40"
          placeholder="مثلاً: اختیارات کمیته ریسک چیست؟"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="flex items-center gap-3 mt-3 text-xs text-muted">
          <label>
            top_k:
            <input
              type="number"
              className="input ml-2 w-20 inline-block"
              value={topK}
              min={1}
              onChange={(e) => setTopK(+e.target.value || 5)}
            />
          </label>
        </div>
        <div className="mt-3">
          <button
            onClick={onAsk}
            disabled={busy}
            className="btn-brand"
          >
            {busy ? "در حال جست‌وجو..." : "بپرس"}
          </button>
        </div>
      </div>

      {/* گفتگو + گراف */}
      <div className="bg-card rounded-2xl shadow-card p-6 lg:col-span-2 border border-border">
        <h2 className="text-lg font-semibold mb-4">💬 گفتگو</h2>

        {!msgs.length ? (
          <p className="text-muted">گفتگویی شروع نشده است.</p>
        ) : (
          <div className="space-y-4">
            {msgs.map((m, i) => (
              <div
                key={i}
                className={`rounded-2xl p-4 border border-border ${m.role === "user" ? "bg-card-2" : "bg-card"}`}
              >
                <div className="text-xs text-muted mb-2">
                  {m.role === "user" ? "کاربر" : "دستیار"} •{" "}
                  {new Date(m.ts).toLocaleString("fa-IR")}
                </div>
                {m.role === "assistant" ? (
                  <Markdown content={m.content} />
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
              </div>
            ))}

            {GraphCard}
          </div>
        )}
      </div>
    </div>
  );
}
