const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type DriveStatus = {
  connected: boolean;
  folder_id: string | null;
  folder_name: string | null;
  last_synced_at: string | null;
};

export type DriveFolder = { id: string; name: string };

export type SyncResult = {
  new_files: number;
  retried: number;
  processed: number;
  failed: number;
  last_synced_at: string;
};

export type Fund = { id: string; name: string; manager: string | null };

export type PerformanceRecord = { period_month: string; return_pct: number | null; nav: number | null; ytd_return_pct: number | null };

export type Extraction = {
  id: string;
  document_type: string | null;
  as_of_date: string | null;
  period_start: string | null;
  period_end: string | null;
  raw_json: Record<string, unknown>;
  commentary_text: string | null;
  low_confidence_fields: string[];
  fund: Fund | null;
  performance_records: PerformanceRecord[];
};

export type Document = {
  id: string;
  filename: string;
  mime_type: string | null;
  source: string;
  status: "pending" | "processing" | "done" | "error";
  error_message: string | null;
  ingested_at: string;
  processed_at: string | null;
  extractions: Extraction[];
};

export type ToolCallTrace = { tool: string; input: Record<string, unknown>; result_preview: string };
export type QueryResponse = { answer: string; tool_calls: ToolCallTrace[]; source_documents: string[] };

export const api = {
  driveStatus: () => request<DriveStatus>("/drive/status"),
  driveAuthUrl: () => request<{ url: string }>("/drive/auth-url"),
  driveFolders: (q?: string) => request<DriveFolder[]>(`/drive/folders${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  driveSelectFolder: (folder_id: string, folder_name: string) =>
    request<DriveStatus>("/drive/select-folder", { method: "POST", body: JSON.stringify({ folder_id, folder_name }) }),
  driveSync: () => request<SyncResult>("/drive/sync", { method: "POST" }),

  funds: () => request<Fund[]>("/funds"),
  documents: (params?: { fund_id?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.fund_id) qs.set("fund_id", params.fund_id);
    if (params?.status) qs.set("status", params.status);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<Document[]>(`/documents${suffix}`);
  },
  uploadDocuments: async (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    const res = await fetch(`${API_URL}/documents/upload`, { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<Document[]>;
  },

  query: (question: string) => request<QueryResponse>("/query", { method: "POST", body: JSON.stringify({ question }) }),
};
