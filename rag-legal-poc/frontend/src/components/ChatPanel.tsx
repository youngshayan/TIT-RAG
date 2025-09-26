import React, { useState } from "react";
import { ask, ChatTurn } from "../api";
import { toast } from "sonner";
import Markdown from "./Markdown";

type Msg = { role: "user" | "assistant"; content: string; ts: number };

export default function ChatPanel(){
  const [q, setQ] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [topK, setTopK] = useState<number>(5);

  const persistHistory = (question: string, answer: any) => {
    try {
      const hist = JSON.parse(localStorage.getItem("chat_hist") || "[]");
      hist.unshift({ q: question, a: answer?.answer ?? "", citations: answer?.citations ?? [], ts: Date.now() });
      localStorage.setItem("chat_hist", JSON.stringify(hist.slice(0, 100)));
    } catch {}
  };

  const onAsk = async ()=>{
    const text = q.trim();
    if(!text){ toast.warning("سؤال را وارد کنید."); return; }

    // append user message
    const newMsgs = [...msgs, { role: "user", content: text, ts: Date.now() }];
    setMsgs(newMsgs);
    setQ("");
    setBusy(true);

    // build short history for backend: last 3 messages BEFORE this question
    const historyForBackend: ChatTurn[] = newMsgs.slice(-3).map(m => ({ role: m.role, content: m.content }));

    try{
      const data = await ask(text, topK, historyForBackend);
      // append assistant
      const withAssistant = [...newMsgs, { role: "assistant", content: String(data?.answer || ""), ts: Date.now() }];
      setMsgs(withAssistant);

      // persist to localStorage (full answer + citations)
      persistHistory(text, data);
    }catch(e:any){
      toast.error(e?.message || "خطا در پرسش");
    }finally{
      setBusy(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="bg-white rounded-2xl shadow-card p-6 lg:col-span-1">
        <h2 className="text-lg font-semibold mb-4">🔎 پرسش</h2>
        <textarea className="w-full h-40 border rounded-xl p-3"
          placeholder="مثلاً: شرایط حداقل موجودی حساب جاری چیست؟"
          value={q} onChange={e=>setQ(e.target.value)} />
        <div className="flex items-center gap-3 mt-3 text-xs text-slate-600">
          <label>top_k:
            <input
              type="number"
              className="ml-2 border rounded px-2 py-1 w-16"
              value={topK}
              min={1}
              onChange={e=>setTopK(+e.target.value||5)}
            />
          </label>
        </div>
        <div className="mt-3">
          <button onClick={onAsk} disabled={busy}
            className="px-5 py-2 rounded-xl bg-brand text-white hover:bg-brand-dark transition disabled:opacity-50">
            {busy ? "در حال جست‌وجو..." : "بپرس"}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-card p-6 lg:col-span-2">
        <h2 className="text-lg font-semibold mb-4">💬 گفتگو</h2>
        {!msgs.length ? (
          <p className="text-slate-500">گفتگویی شروع نشده است.</p>
        ) : (
          <div className="space-y-4">
            {msgs.map((m, i)=>(
              <div key={i} className={`rounded-2xl p-4 ${m.role==="user" ? "bg-slate-100" : "bg-white border"}`}>
                <div className="text-xs text-slate-500 mb-2">
                  {m.role==="user" ? "کاربر" : "دستیار"} • {new Date(m.ts).toLocaleString("fa-IR")}
                </div>
                {m.role==="assistant" ? <Markdown content={m.content} /> : <div className="whitespace-pre-wrap">{m.content}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
