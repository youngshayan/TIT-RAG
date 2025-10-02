// frontend/src/App.tsx
import React, { useEffect, useState } from "react";
import Tabs from "./components/Tabs";
import UploadAnalyze from "./components/UploadAnalyze";
import ChatPanel from "./components/ChatPanel";
import HistoryPanel from "./components/HistoryPanel";
import AdminPanel from "./components/AdminPanel";
import { Toaster } from "sonner";
import { health, API_BASE } from "./api";

type TabKey = "analyze" | "ask" | "history" | "admin";

export default function App(){
  const [tab, setTab] = useState<TabKey>("analyze");
  const [server, setServer] = useState<any>(null);
  const [serverErr, setServerErr] = useState<string | null>(null);

  // Theme
  const [theme, setTheme] = useState<"light"|"dark">(
    (localStorage.getItem("theme") as any) || "dark"
  );
  useEffect(()=>{
    if (theme === "dark") document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(()=>{
    (async ()=>{
      try {
        const h = await health();
        setServer(h);
        setServerErr(null);
        console.log("[health ok]", h);
      } catch (e: any) {
        console.error("[health error]", e);
        setServer(null);
        setServerErr(String(e?.message || e));
      }
    })();
  },[]);

  return (
    <div className="min-h-screen bg-app text-primary">
      <header className="border-b border-border sticky top-0 z-10 bg-card backdrop-blur glass">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          {/* ناحیه لوگوها + عنوان */}
          <div className="flex items-center gap-4">
            {/* لوگوی اصلی: کمی بزرگ‌تر از قبل */}
            {/* مسیر: public/logo.png */}
            <img
              src="/logo.png"
              alt="Logo"
              className="w-18 h-14 rounded-2xl object-contain border border-border"
            />
            {/* لوگوی دوم: هم‌سایز نسخهٔ قبلی (تقریباً 40px) */}
            {/* مسیر: public/logo-2.png  (اختیاری؛ اگر فایل نبود، مخفی می‌ماند) */}
            <img
              src="/logo-2.png"
              alt="Second Logo"
              onError={(e)=>{ (e.currentTarget as HTMLImageElement).style.display='none'; }}
              className="w-14 h-18 rounded-xl object-contain border border-border"
            />

            <div>
              <div className="font-semibold">Inteligent instruction hub</div>
              <div className="text-xs text-muted">بانکی | فارسی | PoC</div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-xs text-muted hidden sm:flex flex-col items-end">
              <div>API: <b className="brand-red">{API_BASE}</b></div>
              {server
                ? <div>Server: <b className="brand-red">{server.index_rows}</b> rows</div>
                : <div>Server: <b>n/a</b> {serverErr ? <span className="brand-red">({serverErr})</span> : null}</div>}
            </div>
            <button
              onClick={()=> setTheme(t=> t==="dark" ? "light" : "dark")}
              className="btn-ghost"
              title="تغییر تم"
            >
              {theme==="dark" ? "☀️ Light" : "🌙 Dark"}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-4">
        <Tabs value={tab} onChange={setTab} />
        {tab==="analyze" && <UploadAnalyze />}
        {tab==="ask" && <ChatPanel />}
        {tab==="history" && <HistoryPanel />}
        {tab==="admin" && <AdminPanel />}
      </main>

      <footer className="max-w-6xl mx-auto px-4 py-8 text-center text-xs text-muted">
        Mindsol Team / Made with ❤️ from iran
      </footer>

      <Toaster position="top-center" richColors />
    </div>
  );
}
