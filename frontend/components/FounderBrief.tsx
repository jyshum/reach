/* eslint-disable @next/next/no-img-element */
import type { CompanyBrief } from "@/lib/types";

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

interface FounderBriefProps {
  brief: CompanyBrief;
}

export default function FounderBrief({ brief }: FounderBriefProps) {
  const displayName = brief.founder_name || brief.name;
  const title = brief.founder_title || "Founder";
  const initials = getInitials(displayName);
  const companyInitials = getInitials(brief.name);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start gap-5">
        <div className="flex w-24 flex-shrink-0 flex-col items-center gap-3">
          {brief.founder_avatar_url ? (
            <img
              src={brief.founder_avatar_url}
              alt={displayName}
              className="h-20 w-20 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-full bg-accent/10 font-display text-2xl text-accent">
              {initials}
            </div>
          )}

          <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-card-border bg-background">
            {brief.small_logo_url ? (
              <img
                src={brief.small_logo_url}
                alt={`${brief.name} logo`}
                className="h-8 w-8 object-contain"
              />
            ) : (
              <span className="text-xs font-semibold text-tertiary">
                {companyInitials}
              </span>
            )}
          </div>
        </div>
        <div>
          <h1 className="font-display text-3xl text-primary">{displayName}</h1>
          <p className="mt-1 text-lg text-secondary">
            {title} · {brief.name}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {brief.yc_batch && (
              <span className="rounded bg-background px-2.5 py-1 text-xs font-medium text-secondary">
                {brief.yc_batch}
              </span>
            )}
            {brief.industry && (
              <span className="rounded bg-background px-2.5 py-1 text-xs text-secondary">
                {brief.industry.replace(/-/g, " ")}
              </span>
            )}
            {brief.team_size && (
              <span className="rounded bg-background px-2.5 py-1 text-xs text-secondary">
                {brief.team_size} people
              </span>
            )}
            {brief.reachability_score && (
              <span
                className={`rounded px-2.5 py-1 text-xs font-semibold uppercase ${reachabilityColor(brief.reachability_score)}`}
              >
                {brief.reachability_score} reachability
              </span>
            )}
          </div>

          {/* Links */}
          <div className="mt-3 flex gap-3">
            {brief.website && (
              <a
                href={brief.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent hover:underline"
              >
                Website
              </a>
            )}
            {brief.founder_linkedin && (
              <a
                href={brief.founder_linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent hover:underline"
              >
                LinkedIn
              </a>
            )}
            {brief.founder_twitter && (
              <a
                href={brief.founder_twitter}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent hover:underline"
              >
                Twitter
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Company Info */}
      <section className="space-y-4">
        {brief.summary && (
          <p className="leading-relaxed text-primary">{brief.summary}</p>
        )}

        {brief.one_liner && (
          <p className="text-sm italic text-secondary">{brief.one_liner}</p>
        )}

        <div className="flex flex-wrap gap-2">
          {brief.stage_detail && (
            <span className="rounded-lg border border-card-border px-3 py-1 text-xs text-secondary">
              {brief.stage_detail}
            </span>
          )}
          {brief.technical_level && (
            <span className="rounded-lg border border-card-border px-3 py-1 text-xs text-secondary">
              {brief.technical_level}
            </span>
          )}
        </div>

        {/* Need tags */}
        {brief.need_tags.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-secondary">
              Skills they need
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {brief.need_tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-accent/10 px-3 py-1 text-xs text-accent"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Specific projects */}
        {brief.specific_projects.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-secondary">
              What you could help with
            </h3>
            <ul className="space-y-2">
              {brief.specific_projects.map((project, i) => (
                <li
                  key={i}
                  className="rounded-lg bg-background p-3 text-sm leading-relaxed text-primary"
                >
                  {project}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
