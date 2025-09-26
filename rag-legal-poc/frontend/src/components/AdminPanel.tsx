// frontend/src/components/AdminPanel.tsx
import React, { useState } from "react";
import { adminUploadIndex } from "../api";
import { toast } from "sonner";

const CATS = ["قوانین و مقررات","آیین‌نامه‌ها","دستورالعمل‌ها","بخشنامه‌ها"];

export default function AdminPanel(){
  const [token, setToken] = useState<string>(() => localStorage.getItem("admin_token") || "");
  const [logged, setLogged] = useState<boolean>(() => !!localStorage.getItem("admin_token"));
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [autoCat, setAutoCat] = useState(true);
  const [cat, setCat] = useState<string>(CATS[0]);
  const [result, setResult] = useState<any>(null);

  const onLogin = ()=>{
    if(!token.trim()){ toast.warning("توکن را وارد کنید."); return; }
    localStorage.setItem("admin_token", token.trim());
    setLogged(true);
    toast.success("وارد شدید.");
  };

  const onLogout = ()=>{
    localStorage.removeItem("admin_token");
    setLogged(false);
    setResult(null);
    toast.success("خارج شدید.");
  };

  const onGo = async ()=>{
    if(!files.length){ toast.warning("فایلی انتخاب نشده."); return; }
    setBusy(true);
    try{
      const data = await adminUploadIndex(files, token.trim(), autoCat, cat);
      setResult(data);
      toast.success("آپلود/ایندکس/نوتیف انجام شد.");
    }catch(e:any){
      toast.error(e?.message || "خطا در عملیات ادمین");
    }finally{
      setBusy(false);
    }
  };

  if(!logged){
    return (
      <div className="bg-white rounded-2xl shadow-card p-6 max-w-md mx-auto">
        <h2 className="text-lg font-semibold mb-4">ورود ادمین</h2>
        <input type="password" value={token} onChange={e=>setToken(e.target.value)}
               placeholder="Admin Token" className="w-full border rounded-xl p-3" />
        <button onClick={onLogin}
          className="mt-3 px-5 py-2 rounded-xl bg-brand text-white hover:bg-brand-dark">ورود</button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-card p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">ادمین: آپلود + ایندکس + دسته‌بندی + ایمیل</h2>
        <button onClick={onLogout} className="text-xs text-red-600 hover:underline">خروج</button>
      </div>

      <div className="grid lg:grid-cols-6 gap-3 mt-4">
        <div className="lg:col-span-2 border rounded-xl p-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={autoCat} onChange={e=>setAutoCat(e.target.checked)} />
            تشخیص خودکار دسته‌بندی
          </label>
          {!autoCat && (
            <select value={cat} onChange={e=>setCat(e.target.value)}
                    className="mt-2 w-full border rounded-xl p-2">
              {CATS.map(c=> <option key={c} value={c}>{c}</option>)}
            </select>
          )}
        </div>
        <input multiple type="file" accept=".pdf,.txt,.text,.md"
               onChange={e=> setFiles(Array.from(e.target.files || []))}
               className="block w-full border rounded-xl p-3 lg:col-span-3" />
        <button onClick={onGo} disabled={busy}
                className="px-5 py-2 rounded-xl bg-brand text-white hover:bg-brand-dark transition disabled:opacity-50">
          {busy ? "در حال اجرا..." : "اجرا"}
        </button>
      </div>

      {!result ? null : (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-[800px] w-full text-sm border">
            <thead className="bg-slate-50">
              <tr>
                <th className="p-2 border">نام فایل</th>
                <th className="p-2 border">دسته‌بندی</th>
                <th className="p-2 border">ایندکس</th>
                <th className="p-2 border">ایمیل</th>
                <th className="p-2 border">گیرندگان</th>
                <th className="p-2 border">مسیر ذخیره</th>
              </tr>
            </thead>
            <tbody>
              {(result.indexed||[]).map((x:any, i:number)=>(
                <tr key={i}>
                  <td className="p-2 border">{x.filename}</td>
                  <td className="p-2 border">{x.category}</td>
                  <td className="p-2 border">{x.indexed ? "✅" : "❌"}</td>
                  <td className="p-2 border">{x.notified ? "✅" : "—"}</td>
                  <td className="p-2 border text-xs">{(x.recipients||[]).join(", ")||"—"}</td>
                  <td className="p-2 border text-xs"><code>{x.stored_path}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
