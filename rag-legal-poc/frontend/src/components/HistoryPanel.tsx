import React, { useEffect, useState } from "react";
import Markdown from "./Markdown";

type HistItem = { q: string; a: string; citations?: any[]; ts: number };

export default function HistoryPanel(){
  const [chat, setChat] = useState<HistItem[]>([]);
  const [open, setOpen] = useState<number | null>(null);

  useEffect(()=>{
    try{ setChat(JSON.parse(localStorage.getItem("chat_hist") || "[]")); }catch{}
  },[]);

  return (
    <div className="bg-white rounded-2xl shadow-card p-6">
      <h3 className="font-semibold mb-4">💬 تاریخچه‌ی پرسش‌ها و پاسخ‌ها</h3>
      {!chat?.length ? (
        <p className="text-slate-500 text-sm">موردی نیست.</p>
      ) : (
        <ul className="space-y-3 text-sm">
          {chat.map((x, i)=>(
            <li key={i} className="border rounded-xl p-3">
              <div className="flex items-center justify-between">
                <div className="font-medium line-clamp-1">Q: {x.q}</div>
                <div className="text-xs text-slate-600">{new Date(x.ts).toLocaleString("fa-IR")}</div>
              </div>
              <div className="mt-2">
                <button
                  onClick={()=> setOpen(open===i ? null : i)}
                  className="text-brand text-xs hover:underline"
                >
                  {open===i ? "بستن پاسخ" : "نمایش پاسخ کامل"}
                </button>
              </div>
              {open===i && (
                <div className="mt-3">
                  <Markdown content={x.a} />
                  {x.citations && x.citations.length ? (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-slate-600">منابع</summary>
                      <pre className="text-xs bg-slate-50 p-2 rounded overflow-auto">{JSON.stringify(x.citations, null, 2)}</pre>
                    </details>
                  ) : null}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
