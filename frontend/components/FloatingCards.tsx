/* eslint-disable @next/next/no-img-element */
"use client";

import type { CompanyCard } from "@/lib/types";

interface FloatingCardsProps {
  companies: CompanyCard[];
}

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function DecorativeFounderCard({ company }: { company: CompanyCard }) {
  const founderName = company.founder_name || company.name;
  const founderInitials = initials(founderName);
  const companyInitials = initials(company.name);
  const tags = (company.yc_tags || []).slice(0, 3);

  return (
    <div className="w-[18rem] rounded-xl border border-card-border/80 bg-card/95 p-4 shadow-float backdrop-blur-sm sm:w-[21rem]">
      <div className="flex gap-4">
        <div className="flex w-14 flex-shrink-0 flex-col items-center gap-2">
          {company.founder_avatar_url ? (
            <img
              src={company.founder_avatar_url}
              alt=""
              className="h-12 w-12 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 font-display text-base text-accent">
              {founderInitials}
            </div>
          )}
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-card-border bg-background">
            {company.small_logo_url ? (
              <img src={company.small_logo_url} alt="" className="h-6 w-6 object-contain" />
            ) : (
              <span className="text-[10px] font-semibold text-tertiary">{companyInitials}</span>
            )}
          </div>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-primary">{founderName}</p>
              <p className="mt-0.5 truncate text-xs text-secondary">
                Founder · {company.name}
              </p>
            </div>
            {company.reachability_score && (
              <span className="rounded bg-reach-high/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-reach-high">
                {company.reachability_score}
              </span>
            )}
          </div>

          {company.one_liner && (
            <p className="mt-2 truncate text-xs text-tertiary">{company.one_liner}</p>
          )}

          <div className="mt-2 flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <span key={tag} className="rounded bg-accent/10 px-2 py-0.5 text-[11px] text-accent">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function FloatingCards({ companies }: FloatingCardsProps) {
  const previewCompanies = companies.slice(0, 12);
  // Duplicate for seamless infinite loop
  const trackCompanies = [...previewCompanies, ...previewCompanies];

  if (previewCompanies.length === 0) return null;

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none relative z-10 mt-7 h-56 w-screen overflow-hidden"
    >
      <div className="landing-card-track flex w-max items-start gap-5 py-2 opacity-90">
        {trackCompanies.map((company, index) => (
          <div key={`${company.id}-${index}`} className="flex-none">
            <DecorativeFounderCard company={company} />
          </div>
        ))}
      </div>
    </div>
  );
}
