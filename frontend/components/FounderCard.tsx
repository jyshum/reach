/* eslint-disable @next/next/no-img-element */
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
  const founderName = company.founder_name || company.name;
  const founderTitle = company.founder_title || "Founder";
  const founderInitials = getInitials(founderName);
  const companyInitials = getInitials(company.name);
  const primaryTags = [
    company.industry,
    company.team_size ? `${company.team_size} people` : null,
    company.match_score > 0
      ? `${company.match_score} interest${company.match_score === 1 ? "" : "s"} match`
      : null,
  ].filter(Boolean);

  const content = (
    <span className="flex items-start gap-4 rounded-xl border border-card-border bg-card p-5 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover">
      <span className="flex w-16 flex-shrink-0 flex-col items-center gap-3 pt-1">
        {company.founder_avatar_url ? (
          <img
            src={company.founder_avatar_url}
            alt={founderName}
            className="h-14 w-14 rounded-full object-cover"
          />
        ) : (
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-accent/10 font-display text-lg text-accent">
            {founderInitials}
          </span>
        )}

        <span className="flex h-11 w-11 items-center justify-center rounded-lg border border-card-border bg-background">
          {company.small_logo_url ? (
            <img
              src={company.small_logo_url}
              alt={`${company.name} logo`}
              className="h-7 w-7 object-contain"
            />
          ) : (
            <span className="text-[11px] font-semibold text-tertiary">
              {companyInitials}
            </span>
          )}
        </span>
      </span>

      <span className="min-w-0 flex-1">
        <span className="flex items-center justify-between gap-3">
          <span className="truncate text-base font-semibold text-primary">
            {founderName}
          </span>
          {company.reachability_score && (
            <span
              className={`flex-shrink-0 rounded px-3 py-1 text-xs font-semibold ${reachabilityColor(company.reachability_score)}`}
            >
              {company.reachability_score === "high"
                ? "High Reachability"
                : company.reachability_score === "medium"
                  ? "Medium Reachability"
                  : "Low Reachability"}
            </span>
          )}
          {(company.email_confidence === "high" || company.email_confidence === "medium") && (
            <span className="flex-shrink-0 rounded bg-teal-100 px-2 py-0.5 text-xs font-medium text-teal-700">
              Email
            </span>
          )}
        </span>

        <span className="mt-0.5 block text-sm text-secondary">
          {founderTitle} · {company.name}
          {company.yc_batch ? ` · ${company.yc_batch}` : ""}
        </span>

        {company.one_liner && (
          <span className="mt-1.5 block truncate text-sm text-tertiary">
            {company.one_liner}
          </span>
        )}

        <span className="mt-2.5 flex flex-wrap gap-1.5">
          {primaryTags.map((tag) => (
            <span
              key={tag}
              className="rounded bg-background px-2 py-0.5 text-xs text-secondary"
            >
              {tag}
            </span>
          ))}
          {(company.yc_tags || []).slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="rounded bg-accent/10 px-2 py-0.5 text-xs text-accent"
            >
              {tag}
            </span>
          ))}
        </span>
      </span>
    </span>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className="block w-full text-left">
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
