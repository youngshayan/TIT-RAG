// frontend/src/App.tsx
import React, { useEffect, useState } from "react";
import Tabs from "./components/Tabs";
import UploadAnalyze from "./components/UploadAnalyze";
import ChatPanel from "./components/ChatPanel";
import HistoryPanel from "./components/HistoryPanel";
import AdminPanel from "./components/AdminPanel";
import { Toaster } from "sonner";
import { health } from "./api";

type TabKey = "analyze" | "ask" | "history" | "admin";

export default function App(){
  const [tab, setTab] = useState<TabKey>("analyze");
  const [server, setServer] = useState<any>(null);

  useEffect(()=>{ health().then(setServer).catch(()=>setServer(null)); },[]);

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
          <div className="text-xs text-slate-500 hidden sm:block">
            {server ? <>Index Rows: <b>{server.index_rows}</b></> : "Server: n/a"}
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
