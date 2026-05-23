"use client";

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

const POSITIONS = [
  { top: "8%", left: "5%", rotate: "-3deg", delay: "0s" },
  { top: "12%", right: "8%", rotate: "2.5deg", delay: "0.5s" },
  { top: "40%", left: "3%", rotate: "1.5deg", delay: "1s" },
  { top: "45%", right: "4%", rotate: "-2deg", delay: "0.3s" },
  { top: "70%", left: "8%", rotate: "2deg", delay: "0.8s" },
  { top: "68%", right: "6%", rotate: "-1.5deg", delay: "0.6s" },
];

interface FloatingCardsProps {
  companies: CompanyCard[];
  onCardClick?: (company: CompanyCard) => void;
}

export default function FloatingCards({
  companies,
  onCardClick,
}: FloatingCardsProps) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {companies.slice(0, 6).map((company, i) => {
        const pos = POSITIONS[i % POSITIONS.length];
        return (
          <div
            key={company.id}
            className="pointer-events-auto absolute animate-float cursor-pointer opacity-60 transition-opacity duration-300 hover:opacity-90"
            style={{
              top: pos.top,
              left: pos.left,
              right: pos.right,
              transform: `rotate(${pos.rotate})`,
              animationDelay: pos.delay,
            }}
            onClick={() => onCardClick?.(company)}
          >
            <div className="flex items-center gap-3 rounded-xl border border-card-border bg-card/90 p-4 shadow-float backdrop-blur-sm">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-accent/10 text-sm font-semibold text-accent">
                {getInitials(company.name)}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-primary">
                  {company.name}
                </p>
                <p className="text-xs text-secondary">
                  Founder
                  {company.yc_batch ? ` · ${company.yc_batch}` : ""}
                </p>
                {company.one_liner && (
                  <p className="mt-0.5 max-w-[200px] truncate text-xs text-tertiary">
                    {company.one_liner}
                  </p>
                )}
              </div>
              {company.reachability_score && (
                <span
                  className={`ml-2 flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${reachabilityColor(company.reachability_score)}`}
                >
                  {company.reachability_score}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
