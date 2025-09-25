// frontend/src/components/SettingsPanel.tsx
import React, { useEffect, useState } from "react";
import { API_BASE } from "../api";

const SettingsPanel: React.FC = () => {
  const [api, setApi] = useState<string>(API_BASE);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    fetch(`${api}/`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [api]);

  return (
    <div className="bg-white rounded-2xl shadow-card p-6">
      <h3 className="font-semibold mb-4">⚙️ تنظیمات</h3>
      <div className="grid sm:grid-cols-2 gap-4 text-sm">
        <label className="block">
          آدرس بک‌اند:
          <input
            className="mt-1 w-full border rounded-xl p-2"
            value={api}
            onChange={(e) => setApi(e.target.value)}
          />
          <div className="text-xs text-slate-500 mt-1">
            برای تغییر دائمی، مقدار <code>API_BASE</code> را در <code>src/api.ts</code> ویرایش کن.
          </div>
        </label>
        <div className="border rounded-xl p-3">
          <div className="font-medium mb-2">وضعیت سرور</div>
          {!health ? (
            <div className="text-slate-500">نامشخص / در دسترس نیست</div>
          ) : (
            <pre className="text-xs bg-slate-50 p-2 rounded overflow-auto">
              {JSON.stringify(health, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
