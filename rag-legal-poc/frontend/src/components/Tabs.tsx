// frontend/src/components/Tabs.tsx
import React from "react";

type TabKey = "analyze" | "ask" | "history" | "admin";

export default function Tabs({ value, onChange }:{ value: TabKey; onChange:(k:TabKey)=>void }){
  // سه تب اول در یک گروه، ادمین در گروه دوم (با فاصله و در انتهای چپ)
  const leftTabs: { key: TabKey; label: string }[] = [
    { key: "analyze", label: "تحلیل" },
    { key: "ask", label: "دستیار" },
    { key: "history", label: "تاریخچه" },
  ];
  const adminTab = { key: "admin", label: "ادمین" };

  const baseBtn =
    "px-4 py-2 rounded-xl transition border text-sm";
  const active = "bg-brand-red text-white border-transparent";
  const inactive = "text-muted hover:bg-card-2 border-border";

  return (
    <div className="flex items-center bg-card p-2 rounded-2xl shadow-card border border-border">
      {/* گروه اصلی تب‌ها */}
      <div className="flex gap-2">
        {leftTabs.map(t => (
          <button
            key={t.key}
            onClick={()=> onChange(t.key)}
            aria-current={value===t.key ? "page" : undefined}
            className={`${baseBtn} ${value===t.key ? active : inactive}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* فاصله‌ انداز (ادمین بره سمت چپِ نوار تب‌ها) */}
      <div className="ml-auto" />

      {/* تب ادمین جدا و در سمت چپ */}
      <button
        onClick={()=> onChange(adminTab.key)}
        aria-current={value===adminTab.key ? "page" : undefined}
        className={`${baseBtn} ${value===adminTab.key ? active : inactive}`}
        title="بخش مدیریت"
      >
        {adminTab.label}
      </button>
    </div>
  );
}
