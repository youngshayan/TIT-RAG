import React, { useState } from "react";
import { ask } from "../api";
import { toast } from "sonner";
import Markdown from "./Markdown";

export default function ChatPanel(){
  const [q, setQ] = useState("");
  const [resp, setResp] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [topK, setTopK] = useState<number>(5);

  const onAsk = async ()=>{
    if(!q.trim()){ toast.warning("سؤال را وارد کنید."); return; }
    setBusy(true);
    try{
      const data = await ask(q, topK);
      setResp(data);
      try {
        const hist = JSON.parse(localStorage.getItem("chat_hist") || "[]");
        hist.unshift({ q, a: data, ts: Date.now() });
        localStorage.setItem("chat_hist", JSON.stringify(hist.slice(0,50)));
      } catch {}
    }catch(e:any){
      toast.error(e?.message || "خطا در پرسش");
    }finally{ setBusy(false); }
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
            <input type="number" className="ml-2 border rounded px-2 py-1 w-16" value={topK} min={1} onChange={e=>setTopK(+e.target.value||5)} />
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
        <h2 className="text-lg font-semibold mb-4">📝 پاسخ</h2>
        {!resp ? <p className="text-slate-500">هنوز پاسخی نیست.</p> :
          <>
            <Markdown content={resp.answer} />
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-slate-600">منابع (citations)</summary>
              <pre className="text-xs bg-slate-50 p-3 rounded-lg overflow-auto">{JSON.stringify(resp.citations, null, 2)}</pre>
            </details>
          </>
        }
      </div>
    </div>
  );
}
