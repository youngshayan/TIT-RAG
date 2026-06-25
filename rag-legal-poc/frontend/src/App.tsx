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

// Language context
export const LanguageContext = React.createContext<{
  lang: "fa" | "en";
  setLang: (lang: "fa" | "en") => void;
  t: (key: string) => string;
}>({
  lang: "fa",
  setLang: () => {},
  t: (key) => key,
});

// Translation dictionary
const translations = {
  fa: {
    app_title: "Intelligent instruction hub",
    app_subtitle: "بانکی | فارسی | PoC",
    api_label: "API",
    server_label: "Server",
    rows_label: "rows",
    theme_light: "☀️ Light",
    theme_dark: "🌙 Dark",
    footer: "Mindsol Team / Made with ❤️ from Iran",
    analyze: "تحلیل",
    ask: "دستیار",
    history: "تاریخچه",
    admin: "ادمین",
  },
  en: {
    app_title: "Intelligent instruction hub",
    app_subtitle: "Banking | English | PoC",
    api_label: "API",
    server_label: "Server",
    rows_label: "rows",
    theme_light: "☀️ Light",
    theme_dark: "🌙 Dark",
    footer: "Mindsol Team / Made with ❤️ from Iran",
    analyze: "Analyze",
    ask: "Assistant",
    history: "History",
    admin: "Admin",
  },
};

export default function App() {
  const [tab, setTab] = useState<TabKey>("analyze");
  const [server, setServer] = useState<any>(null);
  const [serverErr, setServerErr] = useState<string | null>(null);
  const [lang, setLang] = useState<"fa" | "en">(() => {
    return (localStorage.getItem("lang") as "fa" | "en") || "fa";
  });

  // Theme
  const [theme, setTheme] = useState<"light" | "dark">(
    (localStorage.getItem("theme") as any) || "dark"
  );

  const t = (key: string): string => {
    return translations[lang]?.[key as keyof typeof translations.fa] || key;
  };

  useEffect(() => {
    if (theme === "dark") document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("lang", lang);
    document.documentElement.lang = lang === "en" ? "en" : "fa";
    document.documentElement.dir = lang === "en" ? "ltr" : "rtl";
  }, [lang]);

  useEffect(() => {
    (async () => {
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
  }, []);

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      <div className="min-h-screen bg-app text-primary">
        <header className="border-b border-border sticky top-0 z-10 bg-card backdrop-blur glass">
          <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <img
                src="/logo.png"
                alt="Logo"
                className="w-18 h-14 rounded-2xl object-contain border border-border"
              />
              <img
                src="/loخgo-2.png"
                alt="Second Logo"
                onError={(e) => {
                  (e.currentTarget as HTMLImageElement).style.display = "none";
                }}
                className="w-14 h-18 rounded-xl object-contain border border-border"
              />
              <div>
                <div className="font-semibold">{t("app_title")}</div>
                <div className="text-xs text-muted">{t("app_subtitle")}</div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-xs text-muted hidden sm:flex flex-col items-end">
                <div>
                  {t("api_label")}: <b className="brand-red">{API_BASE}</b>
                </div>
                {server ? (
                  <div>
                    {t("server_label")}: <b className="brand-red">{server.index_rows}</b> {t("rows_label")}
                  </div>
                ) : (
                  <div>
                    {t("server_label")}: <b>n/a</b>{" "}
                    {serverErr ? <span className="brand-red">({serverErr})</span> : null}
                  </div>
                )}
              </div>

              <button
                onClick={() => setLang(lang === "fa" ? "en" : "fa")}
                className="btn-ghost text-xs"
                title={lang === "fa" ? "Switch to English" : "تغییر به فارسی"}
              >
                {lang === "fa" ? "🇬🇧 English" : "🇮🇷 فارسی"}
              </button>

              <button
                onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
                className="btn-ghost"
                title={t("theme_change") || "تغییر تم"}
              >
                {theme === "dark" ? t("theme_light") : t("theme_dark")}
              </button>
            </div>
          </div>
        </header>

        <main className="max-w-6xl mx-auto px-4 py-6 space-y-4">
          <Tabs value={tab} onChange={setTab} />
          {tab === "analyze" && <UploadAnalyze />}
          {tab === "ask" && <ChatPanel />}
          {tab === "history" && <HistoryPanel />}
          {tab === "admin" && <AdminPanel />}
        </main>

        <footer className="max-w-6xl mx-auto px-4 py-8 text-center text-xs text-muted">
          {t("footer")}
        </footer>

        <Toaster position="top-center" richColors />
      </div>
    </LanguageContext.Provider>
  );
}