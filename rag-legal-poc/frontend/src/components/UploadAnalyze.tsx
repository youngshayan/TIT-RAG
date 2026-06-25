// frontend/src/components/UploadAnalyze.tsx
import React, { useState, useContext } from "react";
import { uploadAnalyze, AnalyzedFile } from "../api";
import { toast } from "sonner";
import Markdown from "./Markdown";
import { LanguageContext } from "../App";

const texts = {
  fa: {
    title: "📂 تحلیل فوری (خلاصه + بررسی همپوشانی)",
    upload_btn: "ارسال و تحلیل",
    busy: "در حال تحلیل...",
    per_chunk: "per_chunk_candidates:",
    final_k: "final_k:",
    no_file: "فایلی انتخاب نشده.",
    success: "تحلیل انجام شد.",
    error: "خطا در تحلیل",
    summary: "📑 خلاصه",
    conflicts: "⚔️ همپوشانی با اسناد موجود",
    no_conflicts: "همپوشانی یافت نشد یا شواهد کافی نبود.",
    issuer: "صادرکننده",
    number: "شماره",
    date: "تاریخ",
    effective_date: "تاریخ اجرا",
    score: "امتیاز",
    method: "روش",
    verdict: "قضاوت",
    show: "نمایش",
    from_uploaded: "از سند آپلودی:",
    from_db: "از سند موجود:",
    file: "فایل",
    title_col: "عنوان",
    meta_issuer: "صادرکننده",
    meta_number: "شماره",
    meta_date: "تاریخ",
  },
  en: {
    title: "📂 Instant Analysis (Summary + Conflict Check)",
    upload_btn: "Upload & Analyze",
    busy: "Analyzing...",
    per_chunk: "per_chunk_candidates:",
    final_k: "final_k:",
    no_file: "No file selected.",
    success: "Analysis complete.",
    error: "Analysis error",
    summary: "📑 Summary",
    conflicts: "⚔️ Conflicts with existing documents",
    no_conflicts: "No conflicts found or insufficient evidence.",
    issuer: "Issuer",
    number: "Number",
    date: "Date",
    effective_date: "Effective Date",
    score: "Score",
    method: "Method",
    verdict: "Verdict",
    show: "Show",
    from_uploaded: "From uploaded document:",
    from_db: "From existing document:",
    file: "File",
    title_col: "Title",
    meta_issuer: "Issuer",
    meta_number: "Number",
    meta_date: "Date",
  },
};

export default function UploadAnalyze() {
  const { lang } = useContext(LanguageContext);
  const T = texts[lang] || texts.fa;

  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState<AnalyzedFile[] | null>(null);
  const [per, setPer] = useState(3);
  const [limit, setLimit] = useState(15);

  const onUpload = async () => {
    if (!files.length) {
      toast.warning(T.no_file);
      return;
    }
    setBusy(true);
    try {
      const res = await uploadAnalyze(files, per, limit);
      setData(res.analyzed || []);
      toast.success(T.success);
      try {
        localStorage.setItem("last_analyze", JSON.stringify(res.analyzed));
      } catch {}
    } catch (e: any) {
      toast.error(e?.message || T.error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-card rounded-2xl shadow-card p-6 border border-border">
      <h2 className="text-lg font-semibold mb-4">{T.title}</h2>
      <div className="grid sm:grid-cols-3 gap-3">
        <input
          multiple
          type="file"
          accept=".pdf,.txt,.text,.md"
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
          className="input sm:col-span-2"
        />
        <button onClick={onUpload} disabled={busy} className="btn-brand">
          {busy ? T.busy : T.upload_btn}
        </button>
      </div>
      <div className="mt-3 text-xs text-muted flex gap-4">
        <label>
          {T.per_chunk}
          <input
            type="number"
            className="input ml-2 w-20 inline-block"
            value={per}
            min={1}
            onChange={(e) => setPer(+e.target.value || 3)}
          />
        </label>
        <label>
          {T.final_k}
          <input
            type="number"
            className="input ml-2 w-20 inline-block"
            value={limit}
            min={1}
            onChange={(e) => setLimit(+e.target.value || 15)}
          />
        </label>
      </div>

      {!data ? null : (
        <div className="mt-8 space-y-8">
          {data.map((item, idx) => (
            <div key={idx} className="border border-border rounded-2xl p-5 bg-card-2">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold">📄 {item.filename}</h3>
                <div className="text-xs text-muted">
                  {item.meta?.issuer ? (
                    <span className="ml-3">
                      {T.issuer}: {item.meta.issuer}
                    </span>
                  ) : null}
                  {item.meta?.number ? (
                    <span className="ml-3">
                      {T.number}: {item.meta.number}
                    </span>
                  ) : null}
                  {item.meta?.issue_date ? (
                    <span className="ml-3">
                      {T.date}: {item.meta.issue_date}
                    </span>
                  ) : item.meta?.effective_date ? (
                    <span className="ml-3">
                      {T.effective_date}: {item.meta.effective_date}
                    </span>
                  ) : null}
                </div>
              </div>

              <div className="mt-4">
                <h4 className="font-semibold mb-2">{T.summary}</h4>
                <div className="overflow-x-auto bg-card rounded-xl border border-border p-3">
                  <Markdown content={item.summary} />
                </div>
              </div>

              <div className="mt-6">
                <h4 className="font-semibold mb-2">{T.conflicts}</h4>
                {!item.conflicts?.length ? (
                  <p className="text-muted">{T.no_conflicts}</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="table min-w-[720px]">
                      <thead>
                        <tr>
                          <th>{T.title_col}</th>
                          <th>{T.meta_issuer}</th>
                          <th>{T.meta_number}</th>
                          <th>{T.meta_date}</th>
                          <th>{T.score}</th>
                          <th>{T.method}</th>
                          <th>{T.verdict}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.conflicts.map((c, i) => (
                          <tr key={i} className="align-top">
                            <td className="font-medium">{c.db_doc.title || "—"}</td>
                            <td>{c.db_doc.meta?.issuer || "—"}</td>
                            <td>{c.db_doc.meta?.number || "—"}</td>
                            <td>
                              {c.db_doc.meta?.issue_date ||
                                c.db_doc.meta?.effective_date ||
                                "—"}
                            </td>
                            <td>{c.score.toFixed(3)}</td>
                            <td>
                              <span className="badge">{c.source_tag}</span>
                            </td>
                            <td>
                              <details>
                                <summary className="cursor-pointer text-brand">
                                  {T.show}
                                </summary>
                                <div className="mt-2 whitespace-pre-wrap leading-7">
                                  {c.verdict}
                                </div>
                                <div className="grid md:grid-cols-2 gap-3 mt-2">
                                  <div>
                                    <div className="text-muted text-xs">
                                      {T.from_uploaded}
                                    </div>
                                    <div className="bg-card rounded p-2 text-xs border border-border">
                                      {c.snippets.uploaded}
                                    </div>
                                  </div>
                                  <div>
                                    <div className="text-muted text-xs">
                                      {T.from_db}
                                    </div>
                                    <div className="bg-card rounded p-2 text-xs border border-border">
                                      {c.snippets.db}
                                    </div>
                                  </div>
                                </div>
                                <div className="text-xs text-muted mt-2">
                                  {T.file}:{" "}
                                  <code className="font-mono">
                                    {c.db_doc.source_path}
                                  </code>
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