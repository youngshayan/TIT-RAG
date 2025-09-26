// frontend/src/api.ts
export const API_BASE = "http://127.0.0.1:8000";

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

export async function health() {
  const r = await fetch(`${API_BASE}/`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function uploadAnalyze(files: File[], perChunkCandidates=3, finalK=15) {
  const fd = new FormData();
  files.forEach(f => fd.append("files", f));
  fd.append("per_chunk_candidates", String(perChunkCandidates));
  fd.append("final_k", String(finalK));
  const r = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
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
  const r = await fetch(`${API_BASE}/ask`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(await r.text());
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
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<{ ok: boolean; indexed: AdminIndexed[] }>;
}
