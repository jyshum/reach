"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchOutreach } from "@/lib/api";
import type { OutreachEntry } from "@/lib/types";
import StatsHeader from "@/components/StatsHeader";
import OutreachRow from "@/components/OutreachRow";

type FilterChip = "all" | OutreachEntry["status"];

const CHIPS: { label: string; value: FilterChip }[] = [
  { label: "All", value: "all" },
  { label: "Sent", value: "sent" },
  { label: "Replied", value: "replied" },
  { label: "Meeting", value: "meeting" },
  { label: "No Response", value: "no-response" },
];

export default function TrackerPage() {
  const { authenticated, loading: authLoading } = useRequireAuth();

  const [entries, setEntries] = useState<OutreachEntry[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [filter, setFilter] = useState<FilterChip>("all");

  useEffect(() => {
    if (!authenticated) return;

    fetchOutreach()
      .then((data) => setEntries(data))
      .catch(() => {
        // leave empty on error
      })
      .finally(() => setDataLoading(false));
  }, [authenticated]);

  function handleUpdated(updated: OutreachEntry) {
    setEntries((prev) =>
      prev.map((e) => (e.id === updated.id ? updated : e)),
    );
  }

  if (authLoading || dataLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  const filtered =
    filter === "all" ? entries : entries.filter((e) => e.status === filter);

  return (
    <main className="page-enter mx-auto max-w-3xl px-6 py-10">
      <div className="flex flex-col gap-6">
        <h1 className="font-display text-3xl text-primary">Outreach Tracker</h1>

        <StatsHeader entries={entries} />

        {/* Filter chips */}
        <div className="flex flex-wrap gap-2">
          {CHIPS.map((chip) => (
            <button
              key={chip.value}
              onClick={() => setFilter(chip.value)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                filter === chip.value
                  ? "bg-accent text-white"
                  : "bg-card border border-card-border text-secondary hover:text-primary"
              }`}
            >
              {chip.label}
            </button>
          ))}
        </div>

        {/* Outreach list */}
        {filtered.length === 0 ? (
          <div className="rounded-xl border border-card-border bg-card px-6 py-10 text-center">
            {entries.length === 0 ? (
              <p className="text-sm text-secondary">
                No outreach logged yet.{" "}
                <Link href="/feed" className="text-accent hover:underline">
                  Visit a founder&apos;s brief
                </Link>{" "}
                to send your first email.
              </p>
            ) : (
              <p className="text-sm text-secondary">
                No entries match this filter.
              </p>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {filtered.map((entry) => (
              <OutreachRow
                key={entry.id}
                entry={entry}
                showCompanyName
                onUpdated={handleUpdated}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
