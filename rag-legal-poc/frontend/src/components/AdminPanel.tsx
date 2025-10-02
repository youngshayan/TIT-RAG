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
      <div className="bg-card rounded-2xl shadow-card p-6 max-w-md mx-auto border border-border">
        <h2 className="text-lg font-semibold mb-4">ورود ادمین</h2>
        <input type="password" value={token} onChange={e=>setToken(e.target.value)}
               placeholder="رمز عبور" className="input" />
        <button onClick={onLogin}
          className="mt-3 btn-brand w-full">ورود</button>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-2xl shadow-card p-6 border border-border">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">ادمین: آپلود + ایندکس + دسته‌بندی + ایمیل</h2>
        <button onClick={onLogout} className="btn-ghost text-red-300">خروج</button>
      </div>

      <div className="grid lg:grid-cols-6 gap-3 mt-4">
        <div className="lg:col-span-2 border border-border rounded-xl p-3 bg-card-2">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={autoCat} onChange={e=>setAutoCat(e.target.checked)} className="accent-[rgb(214,28,47)]" />
            تشخیص خودکار دسته‌بندی
          </label>
          {!autoCat && (
            <select value={cat} onChange={e=>setCat(e.target.value)} className="select mt-2">
              {CATS.map(c=> <option key={c} value={c}>{c}</option>)}
            </select>
          )}
        </div>
        <input multiple type="file" accept=".pdf,.txt,.text,.md"
               onChange={e=> setFiles(Array.from(e.target.files || []))}
               className="input lg:col-span-3" />
        <button onClick={onGo} disabled={busy}
                className="btn-brand">
          {busy ? "در حال اجرا..." : "اجرا"}
        </button>
      </div>

      {!result ? null : (
        <div className="mt-6 overflow-x-auto">
          <table className="table min-w-[800px]">
            <thead>
              <tr>
                <th>نام فایل</th>
                <th>دسته‌بندی</th>
                <th>ایندکس</th>
                <th>ایمیل</th>
                <th>گیرندگان</th>
                <th>مسیر ذخیره</th>
              </tr>
            </thead>
            <tbody>
              {(result.indexed||[]).map((x:any, i:number)=>(
                <tr key={i}>
                  <td className="font-medium">{x.filename}</td>
                  <td><span className="badge">{x.category}</span></td>
                  <td>{x.indexed ? "✅" : "❌"}</td>
                  <td>{x.notified ? "✅" : "—"}</td>
                  <td className="text-xs">{(x.recipients||[]).join(", ")||"—"}</td>
                  <td className="text-xs font-mono"><code>{x.stored_path}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
