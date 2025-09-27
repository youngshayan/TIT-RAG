// src/components/ChatPanel.tsx
import React, { useState } from "react";
import { ask, ChatTurn } from "../api";
import { toast } from "sonner";
import Markdown from "./Markdown";
import ErrorBoundary from "./ErrorBoundary";
import GraphView from "./GraphView";

type Citation = {
  doc_id: number;
  title: string;
  source_path?: string;
  meta?: any;
  score?: number;
  method?: string;
};

type Msg = {
  role: "user" | "assistant";
  content: string;
  ts: number;
  graph?: any;          // ← گراف Cytoscape (اختیاری)
  citations?: Citation[]; // ← استنادها (اختیاری)
};

export default function ChatPanel() {
  const [q, setQ] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [topK, setTopK] = useState<number>(5);

  const persistHistory = (question: string, answer: any) => {
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
  };

  const onAsk = async () => {
    const text = q.trim();
    if (!text) {
      toast.warning("سؤال را وارد کنید.");
      return;
    }

    // append user message
    const newMsgs: Msg[] = [
      ...msgs,
      { role: "user", content: text, ts: Date.now() },
    ];
    setMsgs(newMsgs);
    setQ("");
    setBusy(true);

    // build short history for backend: last 3 messages BEFORE this question
    const historyForBackend: ChatTurn[] = newMsgs
      .slice(-3)
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      const data: any = await ask(text, topK, historyForBackend); // answer, citations, graph?
      const assistantMsg: Msg = {
        role: "assistant",
        content: String(data?.answer || ""),
        ts: Date.now(),
        citations: Array.isArray(data?.citations) ? data.citations : [],
        graph: data?.graph ?? null,
      };
      setMsgs([...newMsgs, assistantMsg]);

      // persist to localStorage (full answer + citations + graph)
      persistHistory(text, data);
    } catch (e: any) {
      toast.error(e?.message || "خطا در پرسش");
    } finally {
      setBusy(false);
    }
  };

  const CitationList: React.FC<{ items?: Citation[] }> = ({ items }) => {
    if (!items || !items.length) return null;
    return (
      <div className="mt-4">
        <h3 className="text-sm font-semibold mb-2">منابع</h3>
        <ul className="list-disc pr-5 text-sm space-y-1">
          {items.map((c, i) => (
            <li key={i}>
              <span className="font-medium">{c.title || `Doc #${c.doc_id}`}</span>
              {typeof c.score === "number" && (
                <span className="text-slate-500"> — score: {c.score}</span>
              )}
              {c.method && (
                <span className="text-slate-500"> • {c.method}</span>
              )}
              {c.meta?.number && (
                <span className="text-slate-500"> • شماره: {c.meta.number}</span>
              )}
              {c.meta?.issuer && (
                <span className="text-slate-500"> • صادرکننده: {c.meta.issuer}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* پرسش */}
      <div className="bg-white rounded-2xl shadow-card p-6 lg:col-span-1">
        <h2 className="text-lg font-semibold mb-4">🔎 پرسش</h2>
        <textarea
          className="w-full h-40 border rounded-xl p-3"
          placeholder="مثلاً: شرایط حداقل موجودی حساب جاری چیست؟"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="flex items-center gap-3 mt-3 text-xs text-slate-600">
          <label>
            top_k:
            <input
              type="number"
              className="ml-2 border rounded px-2 py-1 w-16"
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
            className="px-5 py-2 rounded-xl bg-brand text-white hover:bg-brand-dark transition disabled:opacity-50"
          >
            {busy ? "در حال جست‌وجو..." : "بپرس"}
          </button>
        </div>
      </div>

      {/* گفتگو */}
      <div className="bg-white rounded-2xl shadow-card p-6 lg:col-span-2">
        <h2 className="text-lg font-semibold mb-4">💬 گفتگو</h2>
        {!msgs.length ? (
          <p className="text-slate-500">گفتگویی شروع نشده است.</p>
        ) : (
          <div className="space-y-4">
            {msgs.map((m, i) => (
              <div
                key={i}
                className={`rounded-2xl p-4 ${
                  m.role === "user" ? "bg-slate-100" : "bg-white border"
                }`}
              >
                <div className="text-xs text-slate-500 mb-2">
                  {m.role === "user" ? "کاربر" : "دستیار"} •{" "}
                  {new Date(m.ts).toLocaleString("fa-IR")}
                </div>

                {m.role === "assistant" ? (
                  <>
                    <Markdown content={m.content} />

                    {/* citations */}
                    <CitationList items={m.citations} />

                    {/* graph */}
                    {m.graph ? (
                      <div className="mt-5">
                        <h3 className="text-sm font-semibold mb-2">
                          نمودار ارتباط (Query → Chunks → Docs)
                        </h3>
                        <ErrorBoundary>
                          <GraphView graph={m.graph} height={480} />
                        </ErrorBoundary>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
