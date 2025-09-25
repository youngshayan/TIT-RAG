import React, { useEffect, useState } from "react";

export default function HistoryPanel(){
  const [analyze, setAnalyze] = useState<any[]>([]);
  const [chat, setChat] = useState<any[]>([]);

  useEffect(()=>{
    try{ setAnalyze(JSON.parse(localStorage.getItem("last_analyze") || "[]")); }catch{}
    try{ setChat(JSON.parse(localStorage.getItem("chat_hist") || "[]")); }catch{}
  },[]);

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="bg-white rounded-2xl shadow-card p-6">
        <h3 className="font-semibold mb-3">📂 آخرین تحلیل‌ها</h3>
        {!analyze?.length ? <p className="text-slate-500 text-sm">موردی نیست.</p> :
          <ul className="space-y-2 text-sm">
            {analyze.map((x:any, i:number)=>(
              <li key={i} className="border rounded-xl p-3">
                <div className="font-medium">{x.filename}</div>
                <div className="text-xs text-slate-600">
                  {x.meta?.issuer ? <span className="ml-3">صادرکننده: {x.meta.issuer}</span> : null}
                  {x.meta?.number ? <span className="ml-3">شماره: {x.meta.number}</span> : null}
                  {x.meta?.issue_date ? <span className="ml-3">تاریخ: {x.meta.issue_date}</span> :
                   x.meta?.effective_date ? <span className="ml-3">تاریخ اجرا: {x.meta.effective_date}</span> : null}
                </div>
              </li>
            ))}
          </ul>
        }
      </div>
      <div className="bg-white rounded-2xl shadow-card p-6">
        <h3 className="font-semibold mb-3">💬 تاریخچه‌ی پرسش‌ها</h3>
        {!chat?.length ? <p className="text-slate-500 text-sm">موردی نیست.</p> :
          <ul className="space-y-2 text-sm">
            {chat.map((x:any, i:number)=>(
              <li key={i} className="border rounded-xl p-3">
                <div className="font-medium">Q: {x.q}</div>
                <div className="text-xs text-slate-600 mt-1">زمان: {new Date(x.ts).toLocaleString("fa-IR")}</div>
              </li>
            ))}
          </ul>
        }
      </div>
    </div>
  );
}
