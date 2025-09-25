// frontend/src/components/Tabs.tsx
import React from "react";

type TabKey = "analyze" | "ask" | "history" | "settings";

interface TabsProps {
  value: TabKey;
  onChange: (k: TabKey) => void;
}

const Tabs: React.FC<TabsProps> = ({ value, onChange }) => {
  const tabs: { key: TabKey; label: string }[] = [
    { key: "analyze", label: "تحلیل (آپلود)" },
    { key: "ask", label: "پرسش" },
    { key: "history", label: "تاریخچه" },
    { key: "settings", label: "تنظیمات" },
  ];

  return (
    <div className="flex gap-2 bg-white p-2 rounded-2xl shadow">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`px-4 py-2 rounded-xl transition ${
            value === t.key
              ? "bg-brand text-white"
              : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
};

export default Tabs;
