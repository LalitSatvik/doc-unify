"use client";

import type { SchemaFieldOut } from "../lib/api";
import { Stamp } from "./Stamp";

export function SchemaPanel({
  fields,
  onRename,
  onSetStatus,
  onRunExtraction,
  running,
  canRun,
}: {
  fields: SchemaFieldOut[];
  onRename: (id: string, name: string) => void;
  onSetStatus: (id: string, status: "approved" | "rejected") => void;
  onRunExtraction: () => void;
  running: boolean;
  canRun: boolean;
}) {
  const approvedCount = fields.filter((f) => f.status === "approved").length;

  return (
    <>
      <div className="sheet">
        <div className="sheet-header">
          <h2>Proposed fields</h2>
          <span className="sheet-header-meta">
            {fields.length} proposed · {approvedCount} approved
          </span>
        </div>
        {fields.length === 0 ? (
          <p className="empty-note">
            No proposals yet -- select ingested documents in Intake and propose a schema.
          </p>
        ) : (
          fields.map((field) => (
            <div className="field-row" key={field.id}>
              <div className="field-row-top">
                <input
                  className="field-name-input"
                  defaultValue={field.name}
                  onBlur={(e) => {
                    if (e.target.value.trim() && e.target.value !== field.name) {
                      onRename(field.id, e.target.value.trim());
                    }
                  }}
                  aria-label={`Field name for ${field.name}`}
                />
                <span className="field-actions">
                  <Stamp
                    variant={
                      field.status === "approved" ? "verified" : field.status === "rejected" ? "rejected" : "flagged"
                    }
                    label={field.status}
                  />
                  {field.status !== "approved" && (
                    <button className="btn btn-ghost btn-sm" type="button" onClick={() => onSetStatus(field.id, "approved")}>
                      Approve
                    </button>
                  )}
                  {field.status !== "rejected" && (
                    <button className="btn btn-ghost btn-sm" type="button" onClick={() => onSetStatus(field.id, "rejected")}>
                      Reject
                    </button>
                  )}
                </span>
              </div>
              <p className="field-def">{field.definition}</p>
              {field.member_labels.length > 0 && (
                <p className="field-members">as written: {field.member_labels.join(" · ")}</p>
              )}
              {field.has_conflict && (
                <p className="conflict-banner">⚠ {field.conflict_reason ?? "This cluster mixes different measurements -- review before approving."}</p>
              )}
            </div>
          ))
        )}
      </div>

      {fields.length > 0 && (
        <p style={{ marginTop: 16 }}>
          <button type="button" className="btn" onClick={onRunExtraction} disabled={!canRun || running}>
            {running ? "Extracting…" : `Extract ${approvedCount || ""} approved field${approvedCount === 1 ? "" : "s"}`}
          </button>
        </p>
      )}
    </>
  );
}
