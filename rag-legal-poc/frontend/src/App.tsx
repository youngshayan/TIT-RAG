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
    <div className="min-h-screen">
      <header className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand/10 flex items-center justify-center text-brand font-bold">R</div>
            <div>
              <div className="font-semibold">RAG Legal Assistant</div>
              <div className="text-xs text-slate-500">بانکی | فارسی | PoC</div>
            </div>
          </div>
          <div className="text-xs text-slate-500 hidden sm:flex flex-col items-end">
            <div>API: <b>{API_BASE}</b></div>
            {server
              ? <div>Server: <b>{server.index_rows}</b> rows</div>
              : <div>Server: <b>n/a</b> {serverErr ? <span className="text-red-500">({serverErr})</span> : null}</div>}
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

      <footer className="max-w-6xl mx-auto px-4 py-8 text-center text-xs text-slate-500">
        ساخته‌شده برای PoC — دقت و UX مهم است. © {new Date().getFullYear()}
      </footer>

      <Toaster position="top-center" richColors />
    </div>
  );
}
