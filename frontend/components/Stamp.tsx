"use client";

import { useState } from "react";

type StampVariant = "verified" | "flagged" | "rejected";

interface Citation {
  document: string;
  page: number | null;
  snippet: string | null;
}

export function Stamp({
  variant,
  label,
  citation,
}: {
  variant: StampVariant;
  label: string;
  citation?: Citation | null;
}) {
  const [open, setOpen] = useState(false);

  return (
    <span className="stamp-wrap">
      <button
        type="button"
        className={`stamp stamp-${variant}`}
        onClick={() => citation && setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={citation ? `${label} -- show source` : label}
      >
        {label}
      </button>
      {open && citation && (
        <div className="stamp-citation" role="note">
          <p className="stamp-citation-doc">
            {citation.document}
            {citation.page ? ` · p.${citation.page}` : ""}
          </p>
          {citation.snippet && <p className="stamp-citation-snippet">&ldquo;{citation.snippet}&rdquo;</p>}
        </div>
      )}
    </span>
  );
}
