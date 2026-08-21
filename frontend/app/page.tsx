"use client";

import { useCallback, useEffect, useState } from "react";
import { ChatPanel } from "../components/ChatPanel";
import { IntakePanel } from "../components/IntakePanel";
import { Rail, type Section } from "../components/Rail";
import { SchemaPanel } from "../components/SchemaPanel";
import { TablePanel } from "../components/TablePanel";
import {
  api,
  type ChatMessage,
  type DocumentOut,
  type ReviewQueueOut,
  type SchemaFieldOut,
  type UnifiedRow,
} from "../lib/api";

const SECTION_COPY: Record<Section, { eyebrow: string; title: string; subtitle: string }> = {
  intake: {
    eyebrow: "01 · Intake",
    title: "Bring in the reports",
    subtitle: "Drop in PDFs, scans, decks, or docx files. Each one is read, chunked, and embedded on arrival.",
  },
  schema: {
    eyebrow: "02 · Schema",
    title: "Reconcile the fields",
    subtitle:
      "Fields that look like the same measurement are proposed as one. Anything that only looks the same is flagged, not merged.",
  },
  table: {
    eyebrow: "03 · Ledger",
    title: "The unified table",
    subtitle: "One row per document, one column per approved field, every cell stamped with its source.",
  },
  chat: {
    eyebrow: "04 · Chat",
    title: "Ask the ledger",
    subtitle: "Drive the same pipeline conversationally -- propose, approve, extract, and explain any cell.",
  },
};

export default function Home() {
  const [section, setSection] = useState<Section>("intake");
  const [documents, setDocuments] = useState<DocumentOut[]>([]);
  const [schemaFields, setSchemaFields] = useState<SchemaFieldOut[]>([]);
  const [unifiedTable, setUnifiedTable] = useState<UnifiedRow[]>([]);
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueOut[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [uploading, setUploading] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [running, setRunning] = useState(false);
  const [sending, setSending] = useState(false);
  const [backendUnreachable, setBackendUnreachable] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const refreshAll = useCallback(async () => {
    try {
      const [docs, fields, table, queue] = await Promise.all([
        api.listDocuments(),
        api.listSchemaFields(),
        api.getUnifiedTable(),
        api.getReviewQueue(),
      ]);
      setDocuments(docs);
      setSchemaFields(fields);
      setUnifiedTable(table);
      setReviewQueue(queue);
      setBackendUnreachable(false);
    } catch {
      setBackendUnreachable(true);
    }
  }, []);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  async function handleUpload(files: FileList) {
    setUploading(true);
    setUploadError(null);
    try {
      for (const file of Array.from(files)) {
        await api.uploadDocument(file);
      }
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed for an unknown reason.");
    } finally {
      // Refresh regardless of outcome: a failed upload may still have left a
      // "failed" row (or earlier files in a batch may have succeeded), and
      // the ledger should reflect that rather than silently omitting it.
      try {
        setDocuments(await api.listDocuments());
      } catch {
        // Backend-unreachable case is already surfaced by refreshAll/the
        // banner below; don't overwrite a more specific upload error with it.
      }
      setUploading(false);
    }
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function handleDiscover() {
    setDiscovering(true);
    try {
      await api.discoverSchema(Array.from(selected));
      setSchemaFields(await api.listSchemaFields());
      setSection("schema");
    } finally {
      setDiscovering(false);
    }
  }

  async function handleRename(id: string, name: string) {
    const field = await api.patchSchemaField(id, { name });
    setSchemaFields((prev) => prev.map((f) => (f.id === id ? field : f)));
  }

  async function handleSetStatus(id: string, status: "approved" | "rejected") {
    const field = await api.patchSchemaField(id, { status });
    setSchemaFields((prev) => prev.map((f) => (f.id === id ? field : f)));
  }

  async function handleRunExtraction() {
    setRunning(true);
    try {
      const approvedIds = schemaFields.filter((f) => f.status === "approved").map((f) => f.id);
      await api.runExtraction(Array.from(selected), approvedIds);
      setUnifiedTable(await api.getUnifiedTable());
      setReviewQueue(await api.getReviewQueue());
      setSection("table");
    } finally {
      setRunning(false);
    }
  }

  async function handleResolve(id: string) {
    await api.resolveReviewItem(id, true);
    setReviewQueue(await api.getReviewQueue());
  }

  async function handleSend(text: string) {
    const next = [...chatMessages, { role: "user" as const, content: text }];
    setChatMessages(next);
    setSending(true);
    try {
      const { reply } = await api.chat(next);
      setChatMessages([...next, { role: "assistant", content: reply }]);
      refreshAll();
    } finally {
      setSending(false);
    }
  }

  const copy = SECTION_COPY[section];
  const approvedCount = schemaFields.filter((f) => f.status === "approved").length;
  const flaggedCount = reviewQueue.filter((q) => !q.resolved).length;

  return (
    <div className="shell">
      <Rail
        active={section}
        onSelect={setSection}
        counts={{ schema: schemaFields.filter((f) => f.status === "proposed").length || undefined, table: flaggedCount || undefined }}
      />
      <main className="stage">
        <header className="stage-header">
          <p className="stage-eyebrow">{copy.eyebrow}</p>
          <h1 className="stage-title">{copy.title}</h1>
          <p className="stage-subtitle">{copy.subtitle}</p>
          {backendUnreachable && (
            <p className="conflict-banner" style={{ marginTop: 12, display: "inline-flex" }}>
              ⚠ Can&rsquo;t reach the backend -- is <code>docker compose up</code> running?
            </p>
          )}
          {uploadError && (
            <p className="conflict-banner" style={{ marginTop: 12, display: "inline-flex" }}>
              ⚠ Upload failed: {uploadError}
            </p>
          )}
        </header>

        {section === "intake" && (
          <IntakePanel
            documents={documents}
            uploading={uploading}
            onUpload={handleUpload}
            selected={selected}
            onToggleSelect={toggleSelect}
            onDiscover={handleDiscover}
            discovering={discovering}
          />
        )}

        {section === "schema" && (
          <SchemaPanel
            fields={schemaFields}
            onRename={handleRename}
            onSetStatus={handleSetStatus}
            onRunExtraction={handleRunExtraction}
            running={running}
            canRun={approvedCount > 0 && selected.size > 0}
          />
        )}

        {section === "table" && (
          <TablePanel
            rows={unifiedTable}
            reviewQueue={reviewQueue}
            onResolve={handleResolve}
            exportUrl={api.exportCsvUrl()}
          />
        )}

        {section === "chat" && <ChatPanel messages={chatMessages} onSend={handleSend} sending={sending} />}
      </main>
    </div>
  );
}
