"use client";

import { useState } from "react";
import { createOutreach } from "@/lib/api";
import type { OutreachEntry } from "@/lib/types";

type Status = OutreachEntry["status"];

const STATUS_OPTIONS: { value: Status; label: string }[] = [
  { value: "sent", label: "Sent" },
  { value: "replied", label: "Replied" },
  { value: "meeting", label: "Meeting" },
  { value: "no-response", label: "No Response" },
];

interface OutreachFormProps {
  companyId: number;
  onCreated: (entry: OutreachEntry) => void;
}

export default function OutreachForm({ companyId, onCreated }: OutreachFormProps) {
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState<Status>("sent");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleCancel() {
    setExpanded(false);
    setStatus("sent");
    setNotes("");
    setError(null);
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const entry = await createOutreach({
        company_id: companyId,
        status,
        notes: notes.trim() || undefined,
        sent_at: new Date().toISOString(),
      });
      onCreated(entry);
      handleCancel();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save outreach.");
    } finally {
      setSaving(false);
    }
  }

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90"
      >
        Log this outreach
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-card-border bg-card p-4 space-y-3">
      {/* Status dropdown */}
      <div>
        <label className="mb-1 block text-xs font-semibold text-secondary">
          Status
        </label>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as Status)}
          className="w-full rounded-lg border border-card-border bg-background px-3 py-2 text-sm text-primary focus:outline-none focus:ring-2 focus:ring-accent/40"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Notes textarea */}
      <div>
        <label className="mb-1 block text-xs font-semibold text-secondary">
          Notes{" "}
          <span className="font-normal text-tertiary">(optional)</span>
        </label>
        <textarea
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What did you say? Any context…"
          className="w-full resize-none rounded-lg border border-card-border bg-background px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-2 focus:ring-accent/40"
        />
      </div>

      {error && <p className="text-xs text-reach-med">{error}</p>}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? "Saving…" : "Save"}
        </button>
        <button
          onClick={handleCancel}
          disabled={saving}
          className="rounded-lg border border-card-border px-4 py-2 text-sm font-semibold text-secondary transition-colors hover:bg-background disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
