"use client";

import { useState, useEffect, use } from "react";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchBrief, fetchOutreach, getGmailStatus, fetchProfile, ApiError } from "@/lib/api";
import type { CompanyBrief, OutreachEntry } from "@/lib/types";
import FounderBrief from "@/components/FounderBrief";
import GuidanceCard from "@/components/GuidanceCard";
import EmailWorkspace from "@/components/EmailWorkspace";
import OutreachForm from "@/components/OutreachForm";
import OutreachRow from "@/components/OutreachRow";

export default function BriefPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { authenticated, loading: authLoading } = useRequireAuth();
  const [brief, setBrief] = useState<CompanyBrief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [outreach, setOutreach] = useState<OutreachEntry[]>([]);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [hasBio, setHasBio] = useState(false);

  useEffect(() => {
    if (!authenticated) return;

    async function load() {
      try {
        const data = await fetchBrief(Number(id));
        setBrief(data);
        const allOutreach = await fetchOutreach();
        setOutreach(allOutreach.filter((e) => e.company_id === Number(id)));
        const gmail = await getGmailStatus().catch(() => ({ connected: false, gmail_email: null }));
        setGmailConnected(gmail.connected);
        const profile = await fetchProfile().catch(() => null);
        setHasBio(!!profile?.bio);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setError("not-found");
        } else {
          setError("unknown");
        }
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [authenticated, id]);

  const handleOutreachCreated = (entry: OutreachEntry) => {
    setOutreach((prev) => [entry, ...prev]);
  };
  const handleOutreachUpdated = (updated: OutreachEntry) => {
    setOutreach((prev) => prev.map((e) => (e.id === updated.id ? { ...e, ...updated } : e)));
  };

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  if (error === "not-found") {
    return (
      <main className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h2 className="font-display text-2xl text-primary">
          Founder not found
        </h2>
        <p className="mt-3 text-secondary">
          This page doesn&apos;t exist or has been removed.
        </p>
      </main>
    );
  }

  if (error || !brief) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h2 className="font-display text-2xl text-primary">
          Something went wrong
        </h2>
        <p className="mt-3 text-secondary">Please try again later.</p>
      </main>
    );
  }

  return (
    <main className="page-enter mx-auto max-w-2xl px-6 py-8">
      <FounderBrief brief={brief} />

      {brief.reachability_factors && brief.reachability_factors.length > 0 && (
        <div className="my-4 rounded-lg border border-card-border bg-card p-4">
          <p className="text-sm font-medium text-primary">
            Why this founder is{" "}
            <span
              className={
                brief.reachability_score === "high"
                  ? "text-reach-high"
                  : brief.reachability_score === "medium"
                    ? "text-reach-med"
                    : "text-reach-low"
              }
            >
              {brief.reachability_score} reachability
            </span>
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {brief.reachability_factors.map((factor) => (
              <span
                key={factor}
                className="rounded-full bg-background px-2.5 py-0.5 text-xs text-secondary"
              >
                {factor}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="my-8">
        <GuidanceCard guidance={brief.guidance} />
      </div>

      <EmailWorkspace
        founderEmail={brief.founder_email}
        emailConfidence={brief.email_confidence}
        companyName={brief.name}
        companyId={brief.id}
        founderName={brief.founder_name}
        founderLinkedin={brief.founder_linkedin}
        gmailConnected={gmailConnected}
        hasBio={hasBio}
      />

      <div className="mt-8 space-y-4">
        <h3 className="font-display text-lg text-primary">Outreach</h3>
        <OutreachForm companyId={brief.id} onCreated={handleOutreachCreated} />
        {outreach.length > 0 && (
          <div className="space-y-2">
            {outreach.map((entry) => (
              <OutreachRow key={entry.id} entry={entry} showCompanyName={false} onUpdated={handleOutreachUpdated} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
