// frontend/src/components/Tabs.tsx
import React, { useContext } from "react";
import { LanguageContext } from "../App";

type TabKey = "analyze" | "ask" | "history" | "admin";

const tabLabels = {
  fa: {
    analyze: "تحلیل",
    ask: "دستیار",
    history: "تاریخچه",
    admin: "ادمین",
  },
  en: {
    analyze: "Analyze",
    ask: "Assistant",
    history: "History",
    admin: "Admin",
  },
};

export default function Tabs({
  value,
  onChange,
}: {
  value: TabKey;
  onChange: (k: TabKey) => void;
}) {
  const { lang } = useContext(LanguageContext);
  const labels = tabLabels[lang] || tabLabels.fa;

  const leftTabs: { key: TabKey; label: string }[] = [
    { key: "analyze", label: labels.analyze },
    { key: "ask", label: labels.ask },
    { key: "history", label: labels.history },
  ];
  const adminTab = { key: "admin", label: labels.admin };

  const baseBtn = "px-4 py-2 rounded-xl transition border text-sm";
  const active = "bg-brand-red text-white border-transparent";
  const inactive = "text-muted hover:bg-card-2 border-border";

  return (
    <div className="flex items-center bg-card p-2 rounded-2xl shadow-card border border-border">
      <div className="flex gap-2">
        {leftTabs.map((t) => (
          <button
            key={t.key}
            onClick={() => onChange(t.key)}
            aria-current={value === t.key ? "page" : undefined}
            className={`${baseBtn} ${value === t.key ? active : inactive}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="ml-auto" />

      <button
        onClick={() => onChange(adminTab.key)}
        aria-current={value === adminTab.key ? "page" : undefined}
        className={`${baseBtn} ${value === adminTab.key ? active : inactive}`}
        title={lang === "en" ? "Admin Panel" : "بخش مدیریت"}
      >
        {adminTab.label}
      </button>
    </div>
  );
}