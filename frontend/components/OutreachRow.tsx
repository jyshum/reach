"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { updateOutreach } from "@/lib/api";
import type { OutreachEntry } from "@/lib/types";

type Status = OutreachEntry["status"];

const STATUS_STYLES: Record<Status, string> = {
  sent: "bg-tertiary/10 text-tertiary",
  replied: "bg-reach-high/10 text-reach-high",
  meeting: "bg-accent/10 text-accent",
  "no-response": "bg-reach-med/10 text-reach-med",
};

const STATUS_LABELS: Record<Status, string> = {
  sent: "Sent",
  replied: "Replied",
  meeting: "Meeting",
  "no-response": "No Response",
};

const ALL_STATUSES: Status[] = ["sent", "replied", "meeting", "no-response"];

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

interface OutreachRowProps {
  entry: OutreachEntry;
  showCompanyName?: boolean;
  onUpdated?: (updated: OutreachEntry) => void;
}

export default function OutreachRow({
  entry,
  showCompanyName = true,
  onUpdated,
}: OutreachRowProps) {
  const [status, setStatus] = useState<Status>(entry.status);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [updating, setUpdating] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    if (dropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [dropdownOpen]);

  async function handleStatusChange(newStatus: Status) {
    if (newStatus === status || updating) return;
    setDropdownOpen(false);
    setUpdating(true);
    try {
      const updated = await updateOutreach(entry.id, { status: newStatus });
      setStatus(updated.status);
      onUpdated?.(updated);
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div className="rounded-xl border border-card-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {showCompanyName && entry.company_name && (
            <Link
              href={`/founder/${entry.company_id}`}
              className="text-sm font-semibold text-primary hover:text-accent transition-colors"
            >
              {entry.company_name}
            </Link>
          )}
          <p className="mt-0.5 text-xs text-tertiary">
            {formatDate(entry.sent_at)}
          </p>
          {entry.notes && (
            <p className="mt-1.5 truncate text-sm text-secondary">
              {entry.notes}
            </p>
          )}
        </div>

        {/* Status badge + dropdown */}
        <div className="relative flex-shrink-0" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen((o) => !o)}
            disabled={updating}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition-opacity ${STATUS_STYLES[status]} ${updating ? "opacity-50 cursor-not-allowed" : "hover:opacity-80 cursor-pointer"}`}
          >
            {STATUS_LABELS[status]}
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 top-full z-10 mt-1 w-36 rounded-lg border border-card-border bg-card shadow-card-hover">
              {ALL_STATUSES.map((s) => (
                <button
                  key={s}
                  onClick={() => handleStatusChange(s)}
                  className={`w-full px-3 py-2 text-left text-xs font-semibold transition-colors first:rounded-t-lg last:rounded-b-lg hover:bg-background ${s === status ? STATUS_STYLES[s] : "text-secondary"}`}
                >
                  {STATUS_LABELS[s]}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
