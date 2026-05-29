"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { fetchCompanies } from "@/lib/api";
import type { CompanyCard } from "@/lib/types";
import SearchBar from "@/components/SearchBar";
import FloatingCards from "@/components/FloatingCards";

const PREVIEW_LIMIT = 12;

export default function LandingPage() {
  const { session, loading: authLoading } = useAuth();
  const router = useRouter();
  const [companies, setCompanies] = useState<CompanyCard[]>([]);
  const [previewLoading, setPreviewLoading] = useState(true);

  useEffect(() => {
    fetchCompanies({ limit: PREVIEW_LIMIT })
      .then(setCompanies)
      .catch(() => {})
      .finally(() => setPreviewLoading(false));
  }, []);

  const handleSearch = useCallback((query: string) => {
    if (!query.trim()) {
      fetchCompanies({ limit: PREVIEW_LIMIT })
        .then(setCompanies)
        .catch(() => {});
      return;
    }
    fetchCompanies({ limit: 50 })
      .then((data) => {
        const q = query.toLowerCase();
        const filtered = data.filter(
          (c) =>
            c.name.toLowerCase().includes(q) ||
            (c.one_liner && c.one_liner.toLowerCase().includes(q)) ||
            (c.industry && c.industry.toLowerCase().includes(q)),
        );
        setCompanies(filtered.slice(0, PREVIEW_LIMIT));
      })
      .catch(() => {});
  }, []);

  const handleSubmit = (query: string) => {
    const encodedQuery = encodeURIComponent(query);
    router.push(
      session ? `/feed?q=${encodedQuery}` : `/login?q=${encodedQuery}`,
    );
  };

  if (authLoading) return null;

  return (
    <main className="page-enter relative isolate flex min-h-screen flex-col items-center overflow-hidden px-6 pt-[4.5rem] pb-8 md:pt-20">
      {/* Decorative background shapes */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        {/* Top-left cluster */}
        <div className="absolute left-[3%] top-10 h-11 w-32 rounded-2xl bg-[#bfeee9]/55" />
        <div className="absolute left-[1%] top-[6.5rem] h-7 w-7 rounded-full bg-[#e2e0fa]/65" />
        <div className="absolute left-[18%] top-5 h-5 w-5 rounded-full bg-accent/30" />

        {/* Top-right */}
        <div className="absolute right-[6%] top-14 h-9 w-40 rounded-xl bg-[#e2e0fa]/55" />
        <div className="absolute right-[3%] top-7 h-6 w-6 rounded-full bg-[#bfeee9]/60" />
        <div className="absolute right-[22%] top-[8.5rem] h-4 w-16 rounded-lg bg-accent/18" />

        {/* Mid-left */}
        <div className="absolute left-[-1.5rem] top-[48%] h-16 w-36 rounded-2xl bg-[#bfeee9]/40" />
        <div className="absolute left-[8%] top-[58%] h-4 w-4 rounded-full bg-[#e2e0fa]/55" />

        {/* Mid-right */}
        <div className="absolute right-[4%] top-[44%] h-10 w-24 rounded-xl bg-[#e2e0fa]/45" />
        <div className="absolute right-[14%] top-[52%] h-5 w-5 rounded-full bg-accent/25" />

        {/* Bottom scatter */}
        <div className="absolute bottom-32 left-[12%] h-6 w-20 rounded-lg bg-[#bfeee9]/35" />
        <div className="absolute bottom-20 right-[10%] h-5 w-5 rounded-full bg-[#e2e0fa]/50" />
        <div className="absolute bottom-44 left-[45%] h-3 w-3 rounded-full bg-accent/20" />
      </div>

      <div className="relative z-10 flex w-full flex-col items-center text-center">
        <h1 className="max-w-3xl font-display text-4xl leading-tight text-primary md:text-5xl">
          <span className="block">You don&apos;t need connections.</span>
          <span className="block">You need the right founder.</span>
        </h1>

        <div className="mt-8 w-full max-w-3xl">
          <SearchBar
            onSearch={handleSearch}
            onSubmit={handleSubmit}
            placeholder="Search AI automation, data pipelines, healthcare, React..."
            size="large"
          />
        </div>
      </div>

      <div className="relative z-10 mt-12 w-screen">
        {previewLoading ? (
          <div
            aria-hidden="true"
            className="pointer-events-none relative z-10 mt-7 h-56 w-screen overflow-hidden"
          >
            <div className="flex w-max items-start gap-5 py-2 opacity-90">
              {Array.from({ length: 8 }).map((_, i) => (
                <div
                  key={i}
                  className="w-[18rem] flex-none rounded-xl border border-card-border/80 bg-card/95 p-4 backdrop-blur-sm sm:w-[21rem]"
                >
                  <div className="flex gap-4">
                    <div className="flex w-14 flex-shrink-0 flex-col items-center gap-2">
                      <div className="h-12 w-12 animate-pulse rounded-full bg-white/10" />
                      <div className="h-9 w-9 animate-pulse rounded-lg bg-white/10" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="h-3.5 w-24 animate-pulse rounded bg-white/10" />
                      <div className="mt-2 h-3 w-32 animate-pulse rounded bg-white/[0.07]" />
                      <div className="mt-3 h-3 w-full animate-pulse rounded bg-white/[0.07]" />
                      <div className="mt-2.5 flex gap-1.5">
                        <div className="h-4 w-14 animate-pulse rounded bg-white/[0.07]" />
                        <div className="h-4 w-16 animate-pulse rounded bg-white/[0.07]" />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <FloatingCards companies={companies} />
        )}
      </div>

      <div className="relative z-10 mt-14 flex flex-col items-center gap-4">
        <div className="flex items-center gap-2.5 text-secondary">
          <img src="/yc-logo.svg" alt="Y Combinator" className="h-5 w-5" />
          <p>A curated directory of 750+ reachable YC founders</p>
        </div>
        <a
          href="/signup"
          className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
        >
          Sign up free
        </a>
      </div>

      <footer className="relative z-10 mt-auto flex w-full max-w-3xl flex-wrap items-center justify-center gap-x-5 gap-y-2 pt-16 text-sm text-tertiary">
        <span>Reach</span>
        <a
          className="transition-colors hover:text-primary"
          href="mailto:jaredshum101@gmail.com"
        >
          Contact
        </a>
      </footer>
    </main>
  );
}
