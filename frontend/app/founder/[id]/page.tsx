"use client";

import { useState, useEffect, use } from "react";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchBrief, ApiError } from "@/lib/api";
import type { CompanyBrief } from "@/lib/types";
import FounderBrief from "@/components/FounderBrief";
import GuidanceCard from "@/components/GuidanceCard";
import EmailWorkspace from "@/components/EmailWorkspace";

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

  useEffect(() => {
    if (!authenticated) return;

    async function load() {
      try {
        const data = await fetchBrief(Number(id));
        setBrief(data);
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError("paywall");
        } else if (err instanceof ApiError && err.status === 404) {
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

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  if (error === "paywall") {
    return (
      <main className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h2 className="font-display text-2xl text-primary">
          You&apos;ve used your 3 free briefs
        </h2>
        <p className="mt-3 text-secondary">
          Complete your profile to unlock unlimited access.
        </p>
      </main>
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
    <main className="mx-auto max-w-2xl px-6 py-8">
      <FounderBrief brief={brief} />

      <div className="my-8">
        <GuidanceCard guidance={brief.guidance} />
      </div>

      <EmailWorkspace
        founderEmail={null}
        companyName={brief.name}
      />
    </main>
  );
}
