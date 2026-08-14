"use client";

import { useState } from "react";
import type { ChatMessage } from "../lib/api";

export function ChatPanel({
  messages,
  onSend,
  sending,
}: {
  messages: ChatMessage[];
  onSend: (text: string) => void;
  sending: boolean;
}) {
  const [draft, setDraft] = useState("");

  function submit() {
    const text = draft.trim();
    if (!text || sending) return;
    onSend(text);
    setDraft("");
  }

  return (
    <div className="sheet">
      <div className="sheet-header">
        <h2>Ask the ledger</h2>
        <span className="sheet-header-meta">tool-calling agent</span>
      </div>
      <div className="chat-log">
        {messages.length === 0 && (
          <p className="empty-note">
            Try: &ldquo;What documents do I have?&rdquo; or &ldquo;Propose a schema from everything I&rsquo;ve
            uploaded.&rdquo;
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.content}
          </div>
        ))}
        {sending && <div className="chat-msg assistant">…</div>}
      </div>
      <div className="chat-input-row">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="Ask about your documents…"
          aria-label="Message"
        />
        <button className="btn" type="button" onClick={submit} disabled={sending}>
          Send
        </button>
      </div>
    </div>
  );
}
