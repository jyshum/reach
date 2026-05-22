"use client";

interface LoadMoreButtonProps {
  onClick: () => void;
  loading: boolean;
  hasMore: boolean;
}

export default function LoadMoreButton({
  onClick,
  loading,
  hasMore,
}: LoadMoreButtonProps) {
  if (!hasMore) return null;

  return (
    <div className="flex justify-center py-8">
      <button
        onClick={onClick}
        disabled={loading}
        className="rounded-lg border border-card-border bg-card px-8 py-2.5 text-sm font-medium text-secondary transition-colors hover:text-primary disabled:opacity-50"
      >
        {loading ? "Loading..." : "Show more founders"}
      </button>
    </div>
  );
}
