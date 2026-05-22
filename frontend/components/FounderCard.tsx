"use client";

import Link from "next/link";
import type { CompanyCard } from "@/lib/types";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function reachabilityColor(score: string | null): string {
  switch (score) {
    case "high":
      return "bg-reach-high/10 text-reach-high";
    case "medium":
      return "bg-reach-med/10 text-reach-med";
    default:
      return "bg-reach-low/10 text-reach-low";
  }
}

interface FounderCardProps {
  company: CompanyCard;
  onClick?: () => void;
}

export default function FounderCard({ company, onClick }: FounderCardProps) {
  const displayName = company.name;
  const initials = getInitials(displayName);

  const content = (
    <div className="flex items-center gap-5 rounded-xl border border-card-border bg-card p-5 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover">
      <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-accent/10 font-display text-lg text-accent">
        {initials}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <h3 className="truncate text-base font-semibold text-primary">
            {displayName}
          </h3>
          {company.reachability_score && (
            <span
              className={`flex-shrink-0 rounded px-2 py-0.5 text-xs font-semibold uppercase ${reachabilityColor(company.reachability_score)}`}
            >
              {company.reachability_score}
            </span>
          )}
        </div>

        <p className="mt-0.5 text-sm text-secondary">
          Founder · {company.name}
          {company.yc_batch ? ` · ${company.yc_batch}` : ""}
        </p>

        {company.one_liner && (
          <p className="mt-1.5 truncate text-sm text-tertiary">
            {company.one_liner}
          </p>
        )}

        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {company.industry && (
            <span className="rounded bg-background px-2 py-0.5 text-xs text-secondary">
              {company.industry}
            </span>
          )}
          {company.team_size && (
            <span className="rounded bg-background px-2 py-0.5 text-xs text-secondary">
              {company.team_size} people
            </span>
          )}
          {company.match_score > 0 && (
            <span className="rounded bg-accent/10 px-2 py-0.5 text-xs text-accent">
              {company.match_score} skill{company.match_score !== 1 ? "s" : ""}{" "}
              match
            </span>
          )}
        </div>
      </div>
    </div>
  );

  if (onClick) {
    return (
      <button onClick={onClick} className="block w-full text-left">
        {content}
      </button>
    );
  }

  return (
    <Link href={`/founder/${company.id}`} className="block">
      {content}
    </Link>
  );
}
