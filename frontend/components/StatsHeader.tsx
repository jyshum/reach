import type { OutreachEntry } from "@/lib/types";

interface StatsHeaderProps {
  entries: OutreachEntry[];
}

export default function StatsHeader({ entries }: StatsHeaderProps) {
  const sent = entries.filter((e) => e.status === "sent").length;
  const replied = entries.filter((e) => e.status === "replied").length;
  const meetings = entries.filter((e) => e.status === "meeting").length;

  const now = new Date();
  const followUps = entries.filter(
    (e) =>
      e.status === "sent" &&
      e.followup_date !== null &&
      new Date(e.followup_date) < now,
  );

  return (
    <div className="flex flex-col gap-3">
      {followUps.length > 0 && (
        <div className="rounded-lg border-l-4 border-guidance-border bg-guidance-bg px-4 py-3 text-sm text-primary">
          You have {followUps.length} follow-up{followUps.length !== 1 ? "s" : ""} due
        </div>
      )}

      <div className="grid grid-cols-3 gap-3">
        {/* Sent */}
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-3xl font-bold text-primary">{sent}</p>
          <p className="mt-1 text-xs text-secondary">Sent</p>
        </div>

        {/* Replied */}
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-3xl font-bold text-reach-high">{replied}</p>
          <p className="mt-1 text-xs text-secondary">Replied</p>
        </div>

        {/* Meetings */}
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-3xl font-bold text-accent">{meetings}</p>
          <p className="mt-1 text-xs text-secondary">Meetings</p>
        </div>
      </div>
    </div>
  );
}
