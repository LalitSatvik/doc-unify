"use client";

import type { ReviewQueueOut, UnifiedRow } from "../lib/api";
import { Stamp } from "./Stamp";

function formatValue(v: number | null): string {
  if (v === null) return "--";
  if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function TablePanel({
  rows,
  reviewQueue,
  onResolve,
  exportUrl,
}: {
  rows: UnifiedRow[];
  reviewQueue: ReviewQueueOut[];
  onResolve: (id: string) => void;
  exportUrl: string;
}) {
  const fieldNames = Array.from(new Set(rows.flatMap((r) => Object.keys(r.cells)))).sort();
  const openItems = reviewQueue.filter((q) => !q.resolved);

  return (
    <>
      <div className="sheet">
        <div className="sheet-header">
          <h2>Unified ledger</h2>
          <a className="btn btn-ghost btn-sm" href={exportUrl} download="doc-unify.csv">
            Export CSV
          </a>
        </div>
        {rows.length === 0 ? (
          <p className="empty-note">Nothing extracted yet -- approve fields in Schema, then extract.</p>
        ) : (
          <div className="ledger-table-scroll">
            <table className="ledger-table">
              <thead>
                <tr>
                  <th>Document</th>
                  {fieldNames.map((name) => (
                    <th key={name}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.document_id}>
                    <td className="doc-cell">{row.document_filename}</td>
                    {fieldNames.map((name) => {
                      const cell = row.cells[name];
                      if (!cell) {
                        return (
                          <td key={name}>
                            <span className="cell-value cell-empty">--</span>
                          </td>
                        );
                      }
                      return (
                        <td key={name}>
                          <span className="cell-value">{formatValue(cell.normalized_value)}</span>{" "}
                          <Stamp
                            variant={cell.needs_review ? "flagged" : "verified"}
                            label={`${Math.round(cell.confidence * 100)}%`}
                            citation={{
                              document: row.document_filename,
                              page: cell.page,
                              snippet: cell.source_snippet,
                            }}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="sheet">
        <div className="sheet-header">
          <h2>Review queue</h2>
          <span className="sheet-header-meta">{openItems.length} open</span>
        </div>
        {openItems.length === 0 ? (
          <p className="empty-note">Nothing flagged -- every cell normalized cleanly.</p>
        ) : (
          openItems.map((item) => (
            <div key={item.id} className="doc-row">
              <span>{item.reason}</span>
              <button className="btn btn-ghost btn-sm" type="button" onClick={() => onResolve(item.id)}>
                Mark resolved
              </button>
            </div>
          ))
        )}
      </div>
    </>
  );
}
