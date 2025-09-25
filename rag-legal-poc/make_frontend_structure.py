# create_frontend_skeleton.py
# -*- coding: utf-8 -*-
"""
ایجاد ساختار و فایل‌های فرانت‌اند برای RAG Legal PoC
به‌صورت پیش‌فرض فایل‌های موجود را دست‌نمی‌زند (skip). با --force بازنویسی می‌کند و .bak می‌سازد.

Usage:
    python create_frontend_skeleton.py --root "D:\\RAG\\pythonProject\\rag-legal-poc"
    python create_frontend_skeleton.py --force
"""

import argparse
import os
from pathlib import Path
from datetime import datetime

PLACEHOLDER = {
    "package.json": """{
  "name": "rag-legal-frontend",
  "version": "0.2.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite --open",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.0.3",
    "remark-gfm": "^4.0.0",
    "sonner": "^1.5.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.2",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.14",
    "@tailwindcss/typography": "^0.5.15",
    "typescript": "^5.6.2",
    "vite": "^5.4.8"
  }
}
""",
    "index.html": """<!doctype html>
<html lang="fa" dir="rtl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1.0" />
    <title>RAG Legal PoC</title>
  </head>
  <body class="bg-slate-50">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
""",
    "tsconfig.json": """{
  "compilerOptions": {
    "target": "ESNext",
    "lib": ["DOM", "DOM.Iterable", "ESNext"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "types": ["vite/client"]
  },
  "include": ["src"]
}
""",
    "vite.config.ts": """import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: "localhost" }
});
""",
    "tailwind.config.cjs": """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html","./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#1f6feb", dark: "#0d419d" }
      },
      boxShadow: { card: "0 8px 24px rgba(31,111,235,0.08)" },
      borderRadius: { xl2: "1rem" }
    },
  },
  plugins: [ require('@tailwindcss/typography') ],
}
""",
    "postcss.config.cjs": """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
""",
    "src/main.tsx": """import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(<App />);
""",
    "src/styles.css": """@tailwind base;
@tailwind components;
@tailwind utilities;

/* RTL helpers */
html[dir="rtl"] .rtl,
html[dir="rtl"] .prose { direction: rtl; text-align: right; }

:root { color-scheme: light; }

body {
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto,
    "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans",
    "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
}
""",
    "src/api.ts": """export const API_BASE = "http://127.0.0.1:8000";

export type Meta = {
  issuer?: string; number?: string;
  issue_date?: string; effective_date?: string;
  filename?: string; [k: string]: any;
};

export type ConflictItem = {
  db_doc: { doc_id: number; title: string; source_path: string; meta: Meta; };
  db_chunk_id: number;
  score: number;
  source_tag: string;
  verdict: string;
  snippets: { uploaded: string; db: string };
  uploaded_meta: Meta;
};

export type AnalyzedFile = {
  filename: string; meta: Meta;
  summary: string; conflicts: ConflictItem[];
};

export async function uploadAnalyze(files: File[], perChunkCandidates=3, finalK=15) {
  const fd = new FormData();
  files.forEach(f => fd.append("files", f));
  fd.append("per_chunk_candidates", String(perChunkCandidates));
  fd.append("final_k", String(finalK));
  const r = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<{ analyzed: AnalyzedFile[] }>;
}

export async function ask(query: string, top_k?: number) {
  const fd = new FormData();
  fd.append("query", query);
  if (top_k) fd.append("top_k", String(top_k));
  const r = await fetch(`${API_BASE}/ask`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function health() {
  const r = await fetch(`${API_BASE}/`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
""",
    "src/components/Tabs.tsx": """import React from "react";
type TabKey = "analyze" | "ask" | "history" | "settings";
export default function Tabs({ value, onChange }:{ value: TabKey; onChange:(k:TabKey)=>void }){
  const tabs: { key: TabKey; label: string }[] = [
    { key: "analyze", label: "تحلیل (آپلود)" },
    { key: "ask", label: "پرسش" },
    { key: "history", label: "تاریخچه" },
    { key: "settings", label: "تنظیمات" },
  ];
  return (
    <div className="flex gap-2 bg-white p-2 rounded-2xl shadow">
      {tabs.map(t => (
        <button key={t.key} onClick={()=> onChange(t.key)}
          className={\`px-4 py-2 rounded-xl transition \${value===t.key ? "bg-brand text-white" : "text-slate-600 hover:bg-slate-100"}\`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}
""",
    "src/components/Markdown.tsx": """import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function Markdown({ content }: { content?: string }) {
  return (
    <div
      className="
        prose prose-slate max-w-none
        text-right [&_*]:text-right rtl
        [&_table]:w-full [&_table]:table-fixed
        [&_th]:text-center [&_td]:align-top
        [&_code]:break-words [&_pre]:overflow-auto
      "
      dir="rtl"
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content || ""}
      </ReactMarkdown>
    </div>
  );
}
""",
    "src/components/UploadAnalyze.tsx": """import React, { useState } from "react";
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
      <h2 className="text-lg font-semibold mb-4">📂 تحلیل فوری (خلاصه + بررسی تعارض) — بدون افزودن به پایگاه</h2>
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
""",
    "src/components/ChatPanel.tsx": """import React, { useState } from "react";
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
""",
    "src/components/HistoryPanel.tsx": """import React, { useEffect, useState } from "react";

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
""",
    "src/components/SettingsPanel.tsx": """import React, { useEffect, useState } from "react";
import { API_BASE } from "../api";

export default function SettingsPanel(){
  const [api, setApi] = useState<string>(API_BASE);
  const [health, setHealth] = useState<any>(null);

  useEffect(()=>{
    fetch(\`\${api}/\`).then(r=>r.json()).then(setHealth).catch(()=>setHealth(null));
  },[api]);

  return (
    <div className="bg-white rounded-2xl shadow-card p-6">
      <h3 className="font-semibold mb-4">⚙️ تنظیمات</h3>
      <div className="grid sm:grid-cols-2 gap-4 text-sm">
        <label className="block">
          آدرس بک‌اند:
          <input className="mt-1 w-full border rounded-xl p-2" value={api} onChange={e=>setApi(e.target.value)} />
          <div className="text-xs text-slate-500 mt-1">برای تغییر دائمی، مقدار API_BASE را در src/api.ts ویرایش کن.</div>
        </label>
        <div className="border rounded-xl p-3">
          <div className="font-medium mb-2">وضعیت سرور</div>
          {!health ? <div className="text-slate-500">نامشخص / در دسترس نیست</div> :
            <pre className="text-xs bg-slate-50 p-2 rounded overflow-auto">{JSON.stringify(health, null, 2)}</pre>
          }
        </div>
      </div>
    </div>
  );
}
""",
    "src/App.tsx": """import React, { useEffect, useState } from "react";
import Tabs from "./components/Tabs";
import UploadAnalyze from "./components/UploadAnalyze";
import ChatPanel from "./components/ChatPanel";
import HistoryPanel from "./components/HistoryPanel";
import SettingsPanel from "./components/SettingsPanel";
import { Toaster } from "sonner";
import { health } from "./api";

type TabKey = "analyze" | "ask" | "history" | "settings";

export default function App(){
  const [tab, setTab] = useState<TabKey>("analyze");
  const [server, setServer] = useState<any>(null);

  useEffect(()=>{
    health().then(setServer).catch(()=>setServer(null));
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
        {tab==="settings" && <SettingsPanel />}
      </main>

      <footer className="max-w-6xl mx-auto px-4 py-8 text-center text-xs text-slate-500">
        ساخته‌شده برای PoC — دقت و UX مهم است. © {new Date().getFullYear()}
      </footer>

      <Toaster position="top-center" richColors />
    </div>
  );
}
"""
}


def write_file(path: Path, content: str, force: bool):
    if path.exists() and not force:
        print(f"⏭️  Skip (exists): {path}")
        return
    if path.exists() and force:
        bak = path.with_suffix(path.suffix + f".{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"🗂️  Backup created: {bak.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"✅ Wrote: {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, default=".", help="پوشه‌ی ریشه‌ی پروژه (حاوی frontend/)")
    ap.add_argument("--force", action="store_true", help="بازنویسی فایل‌های موجود (با ایجاد .bak)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    fe = root / "frontend"

    files_map = {
        fe / "package.json": PLACEHOLDER["package.json"],
        fe / "index.html": PLACEHOLDER["index.html"],
        fe / "tsconfig.json": PLACEHOLDER["tsconfig.json"],
        fe / "vite.config.ts": PLACEHOLDER["vite.config.ts"],
        fe / "tailwind.config.cjs": PLACEHOLDER["tailwind.config.cjs"],
        fe / "postcss.config.cjs": PLACEHOLDER["postcss.config.cjs"],
        fe / "src" / "main.tsx": PLACEHOLDER["src/main.tsx"],
        fe / "src" / "styles.css": PLACEHOLDER["src/styles.css"],
        fe / "src" / "api.ts": PLACEHOLDER["src/api.ts"],
        fe / "src" / "components" / "Tabs.tsx": PLACEHOLDER["src/components/Tabs.tsx"],
        fe / "src" / "components" / "Markdown.tsx": PLACEHOLDER["src/components/Markdown.tsx"],
        fe / "src" / "components" / "UploadAnalyze.tsx": PLACEHOLDER["src/components/UploadAnalyze.tsx"],
        fe / "src" / "components" / "ChatPanel.tsx": PLACEHOLDER["src/components/ChatPanel.tsx"],
        fe / "src" / "components" / "HistoryPanel.tsx": PLACEHOLDER["src/components/HistoryPanel.tsx"],
        fe / "src" / "components" / "SettingsPanel.tsx": PLACEHOLDER["src/components/SettingsPanel.tsx"],
        fe / "src" / "App.tsx": PLACEHOLDER["src/App.tsx"],
    }

    print(f"🏗️  Creating frontend skeleton under: {fe}")
    for p, c in files_map.items():
        write_file(p, c, args.force)

    print("\n🚀 Done. Next steps:")
    print("  1) cd frontend")
    print("  2) npm install")
    print("  3) npm run dev")
    print("  4) (بک‌اند) uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
