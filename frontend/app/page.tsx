"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { fetchCompanies } from "@/lib/api";
import type { CompanyCard } from "@/lib/types";
import SearchBar from "@/components/SearchBar";
import FloatingCards from "@/components/FloatingCards";

const PREVIEW_LIMIT = 20;

export default function LandingPage() {
  const { loading: authLoading } = useAuth();
  const router = useRouter();
  const [companies, setCompanies] = useState<CompanyCard[]>([]);

  // Load initial founder previews.
  useEffect(() => {
    fetchCompanies({ limit: PREVIEW_LIMIT })
      .then(setCompanies)
      .catch(() => {});
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
    router.push(`/login?q=${encodeURIComponent(query)}`);
  };

  const handleCardClick = () => {
    router.push("/login");
  };

  if (authLoading) return null;

  return (
    <main className="relative flex min-h-screen flex-col items-center overflow-x-hidden px-6 pt-24 pb-8 md:pt-28">
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute left-[-8rem] top-24 h-72 w-72 rounded-full border border-accent/15 bg-accent/5" />
        <div className="absolute right-[-10rem] top-48 h-80 w-80 rounded-full border border-card-border bg-card/70" />
        <div className="absolute bottom-20 left-1/2 h-28 w-[34rem] -translate-x-1/2 rounded-full bg-accent/5 blur-3xl" />
      </div>

      <div className="relative z-10 flex w-full flex-col items-center text-center">
        <h1 className="max-w-2xl font-display text-4xl leading-tight text-primary md:text-5xl">
          You don&apos;t need connections. You need the right founder.
        </h1>

        <div className="mt-8 w-full max-w-3xl">
          <SearchBar
            onSearch={handleSearch}
            onSubmit={handleSubmit}
            placeholder="Search AI automation, data pipelines, healthcare, React..."
          />
        </div>
      </div>

      <div className="relative z-10 mt-12 w-screen">
        <FloatingCards companies={companies} onCardClick={handleCardClick} />
      </div>

      <div className="relative z-10 mt-14 flex flex-col items-center gap-4">
        <p className="text-secondary">
          A curated directory of 750+ reachable YC founders
        </p>
        <a
          href="/signup"
          className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
        >
          Sign up free
        </a>
      </div>

      <footer className="relative z-10 mt-auto flex w-full max-w-3xl flex-wrap items-center justify-center gap-x-5 gap-y-2 pt-16 text-sm text-tertiary">
        <span>Reach</span>
        <a className="transition-colors hover:text-primary" href="mailto:hello@example.com">
          Contact
        </a>
        <a className="transition-colors hover:text-primary" href="#replace-linkedin-url">
          LinkedIn
        </a>
        <a className="transition-colors hover:text-primary" href="#replace-x-url">
          X
        </a>
      </footer>
    </main>
  );
}
