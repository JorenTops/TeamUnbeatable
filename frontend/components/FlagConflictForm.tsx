"use client";

import { useState } from "react";
import type { Doc } from "@/lib/types";

export default function FlagConflictForm({
  doc, onSubmit, onCancel,
}: {
  doc: Doc;
  onSubmit: (channel: string, text: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [channel, setChannel] = useState("#payroll-be");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(channel.trim(), text.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <form className="modal" onSubmit={submit} onClick={(e) => e.stopPropagation()}>
        <h3>Flag a Teams contradiction</h3>
        <p className="muted small">On: <strong>{doc.title}</strong>. The document&apos;s trust score is downgraded and its owner is alerted.</p>
        <label>Teams channel
          <input value={channel} onChange={(e) => setChannel(e.target.value)} pattern="#[a-zA-Z0-9][a-zA-Z0-9\-_]{0,48}" required maxLength={50} />
        </label>
        <label>What does the conversation say?
          <textarea value={text} onChange={(e) => setText(e.target.value)} required minLength={10} maxLength={1000} rows={4}
            placeholder="e.g. The client got a correction last month, the 85% rule no longer applies." />
        </label>
        <div className="muted small right">{text.length}/1000</div>
        {error && <div className="error">{error}</div>}
        <div className="actions">
          <button type="button" className="btn" onClick={onCancel}>Cancel</button>
          <button type="submit" className="btn btn-danger" disabled={busy}>{busy ? "Flagging…" : "Flag conflict"}</button>
        </div>
      </form>
    </div>
  );
}
