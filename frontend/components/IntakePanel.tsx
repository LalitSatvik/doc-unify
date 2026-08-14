"use client";

import { useRef, useState } from "react";
import type { DocumentOut } from "../lib/api";

export function IntakePanel({
  documents,
  uploading,
  onUpload,
  selected,
  onToggleSelect,
  onDiscover,
  discovering,
}: {
  documents: DocumentOut[];
  uploading: boolean;
  onUpload: (files: FileList) => void;
  selected: Set<string>;
  onToggleSelect: (id: string) => void;
  onDiscover: () => void;
  discovering: boolean;
}) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <>
      <div
        className={`dropzone${dragActive ? " is-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (e.dataTransfer.files.length) onUpload(e.dataTransfer.files);
        }}
      >
        <p className="dropzone-title">Drop reports here</p>
        <p style={{ margin: "0 0 16px" }}>PDF, PNG/JPG, DOCX, or PPTX -- one at a time or in a batch.</p>
        <button type="button" className="btn" onClick={() => inputRef.current?.click()} disabled={uploading}>
          {uploading ? "Reading…" : "Choose files"}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.docx,.pptx"
          onChange={(e) => e.target.files && onUpload(e.target.files)}
        />
      </div>

      <div className="sheet">
        <div className="sheet-header">
          <h2>Intake log</h2>
          <span className="sheet-header-meta">{documents.length} document{documents.length === 1 ? "" : "s"}</span>
        </div>
        {documents.length === 0 ? (
          <p className="empty-note">Nothing uploaded yet -- drop a report above to start the ledger.</p>
        ) : (
          documents.map((doc) => (
            <label key={doc.id} className="doc-row" style={{ cursor: "pointer" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                <input
                  type="checkbox"
                  checked={selected.has(doc.id)}
                  onChange={() => onToggleSelect(doc.id)}
                  disabled={doc.status !== "ingested"}
                />
                <span style={{ minWidth: 0 }}>
                  <span className="doc-name">{doc.filename}</span>
                  <br />
                  <span className="doc-meta">
                    <span className={`status-dot ${doc.status}`} />
                    {doc.status} · {doc.block_count} blocks · {doc.chunk_count} chunks
                  </span>
                </span>
              </span>
            </label>
          ))
        )}
      </div>

      {documents.some((d) => d.status === "ingested") && (
        <p style={{ marginTop: 16 }}>
          <button type="button" className="btn" onClick={onDiscover} disabled={selected.size === 0 || discovering}>
            {discovering ? "Proposing schema…" : `Propose schema from ${selected.size || ""} selected`}
          </button>
        </p>
      )}
    </>
  );
}
