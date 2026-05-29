export default function SkeletonCard() {
  return (
    <div className="flex items-start gap-4 rounded-xl border border-card-border bg-card p-5">
      {/* Left column: avatar + logo placeholder */}
      <div className="flex w-16 flex-shrink-0 flex-col items-center gap-3 pt-1">
        <div className="h-14 w-14 animate-pulse rounded-full bg-white/10" />
        <div className="h-11 w-11 animate-pulse rounded-lg bg-white/10" />
      </div>

      {/* Right column: text placeholders */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <div className="h-4 w-32 animate-pulse rounded bg-white/10" />
          <div className="h-5 w-14 animate-pulse rounded bg-white/10" />
        </div>

        <div className="mt-2 h-3.5 w-48 animate-pulse rounded bg-white/10" />

        <div className="mt-2 h-3.5 w-64 animate-pulse rounded bg-white/[0.07]" />

        <div className="mt-3 flex gap-1.5">
          <div className="h-5 w-16 animate-pulse rounded bg-white/[0.07]" />
          <div className="h-5 w-20 animate-pulse rounded bg-white/[0.07]" />
          <div className="h-5 w-14 animate-pulse rounded bg-white/[0.07]" />
        </div>
      </div>
    </div>
  );
}
