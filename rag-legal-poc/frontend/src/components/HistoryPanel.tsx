// frontend/src/components/HistoryPanel.tsx
import React, { useEffect, useState, useContext } from "react";
import Markdown from "./Markdown";
import { LanguageContext } from "../App";

type HistItem = { q: string; a: string; citations?: any[]; ts: number };

const texts = {
  fa: {
    title: "💬 تاریخچه‌ی پرسش‌ها و پاسخ‌ها",
    empty: "موردی نیست.",
    q_prefix: "Q:",
    show_answer: "نمایش پاسخ کامل",
    hide_answer: "بستن پاسخ",
    sources: "منابع",
  },
  en: {
    title: "💬 Question & Answer History",
    empty: "No history.",
    q_prefix: "Q:",
    show_answer: "Show full answer",
    hide_answer: "Hide answer",
    sources: "Sources",
  },
};

export default function HistoryPanel() {
  const { lang } = useContext(LanguageContext);
  const T = texts[lang] || texts.fa;

  const [chat, setChat] = useState<HistItem[]>([]);
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => {
    try {
      setChat(JSON.parse(localStorage.getItem("chat_hist") || "[]"));
    } catch {}
  }, []);

  return (
    <div className="bg-card rounded-2xl shadow-card p-6 border border-border">
      <h3 className="font-semibold mb-4">{T.title}</h3>
      {!chat?.length ? (
        <p className="text-muted text-sm">{T.empty}</p>
      ) : (
        <ul className="space-y-3 text-sm">
          {chat.map((x, i) => (
            <li key={i} className="border border-border rounded-2xl p-3 bg-card-2">
              <div className="flex items-center justify-between">
                <div className="font-medium line-clamp-1">
                  {T.q_prefix} {x.q}
                </div>
                <div className="text-xs text-muted">
                  {new Date(x.ts).toLocaleString(lang === "en" ? "en-US" : "fa-IR")}
                </div>
              </div>
              <div className="mt-2">
                <button
                  onClick={() => setOpen(open === i ? null : i)}
                  className="text-xs brand-red hover:underline"
                >
                  {open === i ? T.hide_answer : T.show_answer}
                </button>
              </div>
              {open === i && (
                <div className="mt-3">
                  <Markdown content={x.a} />
                  {x.citations && x.citations.length ? (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-muted">
                        {T.sources}
                      </summary>
                      <pre className="text-xs bg-card rounded p-2 border border-border overflow-auto">
                        {JSON.stringify(x.citations, null, 2)}
                      </pre>
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