// frontend/src/api.ts

/**
 * API base resolution:
 * - از ENV: import.meta.env.VITE_API_BASE
 * - از localStorage: api_base
 * - پیش‌فرض: http://127.0.0.1:8000
 */
function resolveBase(): string {
  const env = (import.meta as any)?.env?.VITE_API_BASE;
  const saved = typeof localStorage !== "undefined" ? localStorage.getItem("api_base") : null;
  return (env || saved || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

export const API_BASE = resolveBase();

export type Meta = {
  issuer?: string;
  number?: string;
  issue_date?: string;
  effective_date?: string;
  filename?: string;
  [k: string]: any;
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
  filename: string;
  meta: Meta;
  summary: string;
  conflicts: ConflictItem[];
};

export type ChatTurn = { role: "user" | "assistant"; content: string };

async function jsonOrText(r: Response) {
  const ct = r.headers.get("content-type") || "";
  if (ct.includes("application/json")) return r.json();
  return r.text();
}

// --- ساده: ساخت/گرفتن sid جلسه ---
function getOrCreateSID(): string {
  try {
    let sid = localStorage.getItem("chat_sid");
    if (sid && sid.length > 0) return sid;
    // تلاش برای UUID
    if (typeof crypto !== "undefined" && (crypto as any).randomUUID) {
      sid = (crypto as any).randomUUID();
    } else {
      sid = "sid_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    }
    localStorage.setItem("chat_sid", sid);
    return sid;
  } catch {
    return "sid_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }
}

export async function health() {
  const url = `${API_BASE}/health`;
  const r = await fetch(url, { method: "GET" });
  if (!r.ok) throw new Error(String(await jsonOrText(r)));
  return r.json();
}

export async function uploadAnalyze(files: File[], perChunkCandidates=3, finalK=15) {
  const fd = new FormData();
  files.forEach(f => fd.append("files", f));
  fd.append("per_chunk_candidates", String(perChunkCandidates));
  fd.append("final_k", String(finalK));
  const r = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(String(await jsonOrText(r)));
  return r.json() as Promise<{ analyzed: AnalyzedFile[] }>;
}

export async function ask(query: string, top_k?: number, history?: ChatTurn[]) {
  const fd = new FormData();
  fd.append("query", query);
  if (top_k) fd.append("top_k", String(top_k));
  if (history && history.length) {
    const last3 = history.slice(-3);
    fd.append("history", JSON.stringify(last3));
  }
  // ← اضافه شد: sid برای «حافظهٔ جلسه»
  fd.append("sid", getOrCreateSID());

  const r = await fetch(`${API_BASE}/ask`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(String(await jsonOrText(r)));
  return r.json();
}

// -------- Admin --------
export type AdminIndexed = {
  filename: string;
  category: string;
  indexed: boolean;
  notified: boolean;
  recipients: string[];
  stored_path: string;
};

export async function adminUploadIndex(files: File[], adminToken: string, autoCategory: boolean, category?: string) {
  const fd = new FormData();
  files.forEach(f => fd.append("files", f));
  fd.append("auto_category", String(autoCategory));
  if (!autoCategory && category) fd.append("category", category);

  const r = await fetch(`${API_BASE}/admin/upload_and_index`, {
    method: "POST",
    body: fd,
    headers: { "X-Admin-Token": adminToken }
  });
  if (!r.ok) throw new Error(String(await jsonOrText(r)));
  return r.json() as Promise<{ ok: boolean; indexed: AdminIndexed[] }>;
}
