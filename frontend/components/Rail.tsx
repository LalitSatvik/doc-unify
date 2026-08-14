"use client";

export type Section = "intake" | "schema" | "table" | "chat";

const TABS: { id: Section; label: string }[] = [
  { id: "intake", label: "Intake" },
  { id: "schema", label: "Schema" },
  { id: "table", label: "Ledger" },
  { id: "chat", label: "Chat" },
];

export function Rail({
  active,
  onSelect,
  counts,
}: {
  active: Section;
  onSelect: (s: Section) => void;
  counts: Partial<Record<Section, number>>;
}) {
  return (
    <nav className="rail" aria-label="Sections">
      <div className="rail-mark" aria-hidden="true">
        du
      </div>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className="rail-tab"
          aria-current={active === tab.id}
          onClick={() => onSelect(tab.id)}
        >
          {!!counts[tab.id] && <span className="rail-tab-count">{counts[tab.id]}</span>}
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
