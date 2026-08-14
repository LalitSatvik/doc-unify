// Thin fetch wrappers over the backend, proxied through Next's rewrite
// (see next.config.mjs) so the browser only ever talks to same-origin
// /api/*.

export type DocumentStatus = "pending" | "ingested" | "failed";

export interface DocumentOut {
  id: string;
  filename: string;
  content_type: string;
  status: DocumentStatus;
  block_count: number;
  chunk_count: number;
}

export type SchemaFieldStatus = "proposed" | "approved" | "rejected";

export interface SchemaFieldOut {
  id: string;
  name: string;
  definition: string;
  status: SchemaFieldStatus;
  has_conflict: boolean;
  conflict_reason: string | null;
  member_labels: string[];
}

export interface UnifiedCell {
  raw_value: string | null;
  raw_unit: string | null;
  normalized_value: number | null;
  confidence: number;
  needs_review: boolean;
  page: number | null;
  source_snippet: string | null;
}

export interface UnifiedRow {
  document_id: string;
  document_filename: string;
  cells: Record<string, UnifiedCell>;
}

export interface ReviewQueueOut {
  id: string;
  table_cell_id: string;
  reason: string;
  resolved: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return response.json();
}

export const api = {
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentOut>("/documents", { method: "POST", body: form });
  },
  listDocuments: () => request<DocumentOut[]>("/documents"),

  discoverSchema: (documentIds: string[]) =>
    request<SchemaFieldOut[]>("/schema/discover", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds }),
    }),
  listSchemaFields: () => request<SchemaFieldOut[]>("/schema/fields"),
  patchSchemaField: (id: string, patch: { name?: string; status?: SchemaFieldStatus }) =>
    request<SchemaFieldOut>(`/schema/fields/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),

  runExtraction: (documentIds: string[], schemaFieldIds: string[]) =>
    request<unknown[]>("/extraction/run", {
      method: "POST",
      body: JSON.stringify({ document_ids: documentIds, schema_field_ids: schemaFieldIds }),
    }),
  getUnifiedTable: () => request<UnifiedRow[]>("/extraction/table"),
  getReviewQueue: () => request<ReviewQueueOut[]>("/extraction/review-queue"),
  resolveReviewItem: (id: string, resolved: boolean) =>
    request<ReviewQueueOut>(`/extraction/review-queue/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ resolved }),
    }),
  exportCsvUrl: () => "/api/extraction/export.csv",

  chat: (messages: ChatMessage[]) =>
    request<{ reply: string }>("/chat", { method: "POST", body: JSON.stringify({ messages }) }),
};
