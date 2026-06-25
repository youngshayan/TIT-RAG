// frontend/src/components/AdminPanel.tsx
import React, { useState, useContext } from "react";
import { adminUploadIndex } from "../api";
import { toast } from "sonner";
import { LanguageContext } from "../App";

const CATS_FA = ["قوانین و مقررات", "آیین‌نامه‌ها", "دستورالعمل‌ها", "بخشنامه‌ها"];
const CATS_EN = ["Laws and Regulations", "Bylaws", "Guidelines", "Circulars"];

const texts = {
  fa: {
    title: "ادمین: آپلود + ایندکس + دسته‌بندی + ایمیل",
    login_title: "ورود ادمین",
    password_placeholder: "رمز عبور",
    login_btn: "ورود",
    logout_btn: "خروج",
    token_warning: "توکن را وارد کنید.",
    login_success: "وارد شدید.",
    logout_success: "خارج شدید.",
    no_file: "فایلی انتخاب نشده.",
    upload_success: "آپلود/ایندکس/نوتیف انجام شد.",
    upload_error: "خطا در عملیات ادمین",
    busy: "در حال اجرا...",
    execute: "اجرا",
    auto_category: "تشخیص خودکار دسته‌بندی",
    filename: "نام فایل",
    category: "دسته‌بندی",
    index: "ایندکس",
    email: "ایمیل",
    recipients: "گیرندگان",
    stored_path: "مسیر ذخیره",
  },
  en: {
    title: "Admin: Upload + Index + Categorize + Email",
    login_title: "Admin Login",
    password_placeholder: "Password",
    login_btn: "Login",
    logout_btn: "Logout",
    token_warning: "Please enter token.",
    login_success: "Logged in.",
    logout_success: "Logged out.",
    no_file: "No file selected.",
    upload_success: "Upload/Index/Notify completed.",
    upload_error: "Admin operation error",
    busy: "Running...",
    execute: "Execute",
    auto_category: "Auto-categorization",
    filename: "Filename",
    category: "Category",
    index: "Index",
    email: "Email",
    recipients: "Recipients",
    stored_path: "Stored Path",
  },
};

export default function AdminPanel() {
  const { lang } = useContext(LanguageContext);
  const T = texts[lang] || texts.fa;
  const CATS = lang === "en" ? CATS_EN : CATS_FA;

  const [token, setToken] = useState<string>(() => localStorage.getItem("admin_token") || "");
  const [logged, setLogged] = useState<boolean>(() => !!localStorage.getItem("admin_token"));
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [autoCat, setAutoCat] = useState(true);
  const [cat, setCat] = useState<string>(CATS[0]);
  const [result, setResult] = useState<any>(null);

  const onLogin = () => {
    if (!token.trim()) {
      toast.warning(T.token_warning);
      return;
    }
    localStorage.setItem("admin_token", token.trim());
    setLogged(true);
    toast.success(T.login_success);
  };

  const onLogout = () => {
    localStorage.removeItem("admin_token");
    setLogged(false);
    setResult(null);
    toast.success(T.logout_success);
  };

  const onGo = async () => {
    if (!files.length) {
      toast.warning(T.no_file);
      return;
    }
    setBusy(true);
    try {
      const data = await adminUploadIndex(files, token.trim(), autoCat, cat);
      setResult(data);
      toast.success(T.upload_success);
    } catch (e: any) {
      toast.error(e?.message || T.upload_error);
    } finally {
      setBusy(false);
    }
  };

  if (!logged) {
    return (
      <div className="bg-card rounded-2xl shadow-card p-6 max-w-md mx-auto border border-border">
        <h2 className="text-lg font-semibold mb-4">{T.login_title}</h2>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder={T.password_placeholder}
          className="input"
        />
        <button onClick={onLogin} className="mt-3 btn-brand w-full">
          {T.login_btn}
        </button>
      </div>
    );
  }

  return (
    <div className="bg-card rounded-2xl shadow-card p-6 border border-border">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{T.title}</h2>
        <button onClick={onLogout} className="btn-ghost text-red-300">
          {T.logout_btn}
        </button>
      </div>

      <div className="grid lg:grid-cols-6 gap-3 mt-4">
        <div className="lg:col-span-2 border border-border rounded-xl p-3 bg-card-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoCat}
              onChange={(e) => setAutoCat(e.target.checked)}
              className="accent-[rgb(214,28,47)]"
            />
            {T.auto_category}
          </label>
          {!autoCat && (
            <select
              value={cat}
              onChange={(e) => setCat(e.target.value)}
              className="select mt-2"
            >
              {CATS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          )}
        </div>
        <input
          multiple
          type="file"
          accept=".pdf,.txt,.text,.md"
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
          className="input lg:col-span-3"
        />
        <button onClick={onGo} disabled={busy} className="btn-brand">
          {busy ? T.busy : T.execute}
        </button>
      </div>

      {!result ? null : (
        <div className="mt-6 overflow-x-auto">
          <table className="table min-w-[800px]">
            <thead>
              <tr>
                <th>{T.filename}</th>
                <th>{T.category}</th>
                <th>{T.index}</th>
                <th>{T.email}</th>
                <th>{T.recipients}</th>
                <th>{T.stored_path}</th>
              </tr>
            </thead>
            <tbody>
              {(result.indexed || []).map((x: any, i: number) => (
                <tr key={i}>
                  <td className="font-medium">{x.filename}</td>
                  <td>
                    <span className="badge">{x.category}</span>
                  </td>
                  <td>{x.indexed ? "✅" : "❌"}</td>
                  <td>{x.notified ? "✅" : "—"}</td>
                  <td className="text-xs">{(x.recipients || []).join(", ") || "—"}</td>
                  <td className="text-xs font-mono">
                    <code>{x.stored_path}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}