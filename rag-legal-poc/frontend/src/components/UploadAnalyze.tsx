import React, { useState } from "react";
import { uploadAnalyze, AnalyzedFile } from "../api";
import { toast } from "sonner";
import Markdown from "./Markdown";

export default function UploadAnalyze(){
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState<AnalyzedFile[]|null>(null);
  const [per, setPer] = useState(3);
  const [limit, setLimit] = useState(15);

  const onUpload = async ()=>{
    if(!files.length){ toast.warning("فایلی انتخاب نشده."); return; }
    setBusy(true);
    try{
      const res = await uploadAnalyze(files, per, limit);
      setData(res.analyzed || []);
      toast.success("تحلیل انجام شد.");
      try { localStorage.setItem("last_analyze", JSON.stringify(res.analyzed)); } catch {}
    }catch(e:any){
      toast.error(e?.message || "خطا در تحلیل");
    }finally{ setBusy(false); }
  };

  return (
    <div className="bg-white rounded-2xl shadow-card p-6">
      <h2 className="text-lg font-semibold mb-4">📂 تحلیل فوری (خلاصه + بررسی تعارض)</h2>
      <div className="grid sm:grid-cols-3 gap-3">
        <input multiple type="file" accept=".pdf,.txt,.text,.md"
               onChange={e=> setFiles(Array.from(e.target.files || []))}
               className="block w-full border rounded-xl p-3 sm:col-span-2" />
        <button onClick={onUpload} disabled={busy}
                className="px-5 py-2 rounded-xl bg-brand text-white hover:bg-brand-dark transition disabled:opacity-50">
          {busy ? "در حال تحلیل..." : "ارسال و تحلیل"}
        </button>
      </div>
      <div className="mt-3 text-xs text-slate-600 flex gap-4">
        <label>per_chunk_candidates:
          <input type="number" className="ml-2 border rounded px-2 py-1 w-16" value={per} min={1} onChange={e=>setPer(+e.target.value||3)}/>
        </label>
        <label>final_k:
          <input type="number" className="ml-2 border rounded px-2 py-1 w-16" value={limit} min={1} onChange={e=>setLimit(+e.target.value||15)}/>
        </label>
      </div>

      {!data ? null : (
        <div className="mt-8 space-y-8">
          {data.map((item, idx)=>(
            <div key={idx} className="border rounded-2xl p-5">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold">📄 {item.filename}</h3>
                <div className="text-xs text-slate-500">
                  {item.meta?.issuer ? <span className="ml-3">صادرکننده: {item.meta.issuer}</span> : null}
                  {item.meta?.number ? <span className="ml-3">شماره: {item.meta.number}</span> : null}
                  {item.meta?.issue_date ? <span className="ml-3">تاریخ: {item.meta.issue_date}</span> :
                   item.meta?.effective_date ? <span className="ml-3">تاریخ اجرا: {item.meta.effective_date}</span> : null}
                </div>
              </div>

              <div className="mt-4">
                <h4 className="font-semibold mb-2">📑 خلاصه</h4>
                <div className="overflow-x-auto">
                  <Markdown content={item.summary} />
                </div>
              </div>

              <div className="mt-6">
                <h4 className="font-semibold mb-2">⚔️ تعارض با اسناد موجود</h4>
                {!item.conflicts?.length ? (
                  <p className="text-slate-500">تعارضی یافت نشد یا شواهد کافی نبود.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-[720px] w-full text-sm border">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="p-2 border">عنوان</th>
                          <th className="p-2 border">صادرکننده</th>
                          <th className="p-2 border">شماره</th>
                          <th className="p-2 border">تاریخ</th>
                          <th className="p-2 border">امتیاز</th>
                          <th className="p-2 border">روش</th>
                          <th className="p-2 border">قضاوت</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.conflicts.map((c, i)=>(
                          <tr key={i} className="align-top">
                            <td className="p-2 border">{c.db_doc.title || "—"}</td>
                            <td className="p-2 border">{c.db_doc.meta?.issuer || "—"}</td>
                            <td className="p-2 border">{c.db_doc.meta?.number || "—"}</td>
                            <td className="p-2 border">{c.db_doc.meta?.issue_date || c.db_doc.meta?.effective_date || "—"}</td>
                            <td className="p-2 border">{c.score.toFixed(3)}</td>
                            <td className="p-2 border">{c.source_tag}</td>
                            <td className="p-2 border">
                              <details>
                                <summary className="cursor-pointer text-brand">نمایش</summary>
                                <div className="mt-2 whitespace-pre-wrap leading-7">{c.verdict}</div>
                                <div className="grid md:grid-cols-2 gap-3 mt-2">
                                  <div>
                                    <div className="text-slate-600 text-xs">از سند آپلودی:</div>
                                    <div className="bg-slate-50 rounded p-2 text-xs">{c.snippets.uploaded}</div>
                                  </div>
                                  <div>
                                    <div className="text-slate-600 text-xs">از سند موجود:</div>
                                    <div className="bg-slate-50 rounded p-2 text-xs">{c.snippets.db}</div>
                                  </div>
                                </div>
                                <div className="text-xs text-slate-500 mt-2">
                                  فایل: <code>{c.db_doc.source_path}</code>
                                </div>
                              </details>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
