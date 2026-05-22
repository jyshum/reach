import type { Guidance } from "@/lib/types";

interface GuidanceCardProps {
  guidance: Guidance | null;
}

function GuidanceField({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <dt className="text-sm font-semibold text-accent">{label}</dt>
      <dd className="mt-1 text-sm leading-relaxed text-primary">{text}</dd>
    </div>
  );
}

export default function GuidanceCard({ guidance }: GuidanceCardProps) {
  if (!guidance) {
    return (
      <div className="rounded-xl border border-card-border bg-card p-6">
        <p className="text-sm text-secondary">
          Add skills to your profile to get personalized guidance.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-l-4 border-guidance-border bg-guidance-bg p-6">
      <h3 className="mb-4 font-display text-lg text-primary">Your Approach</h3>
      <dl className="space-y-4">
        <GuidanceField label="Your angle" text={guidance.your_angle} />
        <GuidanceField label="Reference this" text={guidance.reference_this} />
        <GuidanceField label="Don't say" text={guidance.dont_say} />
        <GuidanceField label="Your ask" text={guidance.your_ask} />
      </dl>
    </div>
  );
}
