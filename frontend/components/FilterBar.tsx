"use client";

import { INDUSTRIES } from "@/lib/types";

interface FilterBarProps {
  industry: string;
  reachability: string;
  onIndustryChange: (value: string) => void;
  onReachabilityChange: (value: string) => void;
}

const REACHABILITY_OPTIONS = ["all", "high", "medium", "low"];

export default function FilterBar({
  industry,
  reachability,
  onIndustryChange,
  onReachabilityChange,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={industry}
        onChange={(e) => onIndustryChange(e.target.value)}
        className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary focus:border-accent focus:outline-none"
      >
        <option value="">All industries</option>
        {INDUSTRIES.map((ind) => (
          <option key={ind} value={ind}>
            {ind.replace(/-/g, " ")}
          </option>
        ))}
      </select>

      <div className="flex gap-1.5">
        {REACHABILITY_OPTIONS.map((level) => (
          <button
            key={level}
            onClick={() =>
              onReachabilityChange(level === "all" ? "" : level)
            }
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              (level === "all" && reachability === "") ||
              level === reachability
                ? "bg-accent text-white"
                : "bg-card text-secondary border border-card-border hover:text-primary"
            }`}
          >
            {level.charAt(0).toUpperCase() + level.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
}
