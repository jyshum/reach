"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { fetchCompanies } from "@/lib/api";
import type { CompanyCard } from "@/lib/types";
import SearchBar from "@/components/SearchBar";
import FloatingCards from "@/components/FloatingCards";

export default function LandingPage() {
  const { session, loading: authLoading } = useAuth();
  const router = useRouter();
  const [companies, setCompanies] = useState<CompanyCard[]>([]);

  // Redirect logged-in users to feed
  useEffect(() => {
    if (!authLoading && session) {
      router.replace("/feed");
    }
  }, [session, authLoading, router]);

  // Load initial floating cards
  useEffect(() => {
    fetchCompanies({ limit: 6 })
      .then(setCompanies)
      .catch(() => {});
  }, []);

  const handleSearch = useCallback((query: string) => {
    if (!query.trim()) {
      fetchCompanies({ limit: 6 })
        .then(setCompanies)
        .catch(() => {});
      return;
    }
    fetchCompanies({ limit: 50 }).then((data) => {
      const q = query.toLowerCase();
      const filtered = data.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          (c.one_liner && c.one_liner.toLowerCase().includes(q)) ||
          (c.industry && c.industry.toLowerCase().includes(q)),
      );
      setCompanies(filtered.slice(0, 6));
    }).catch(() => {});
  }, []);

  const handleSubmit = (query: string) => {
    router.push(`/login?q=${encodeURIComponent(query)}`);
  };

  const handleCardClick = () => {
    router.push("/login");
  };

  if (authLoading) return null;

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6">
      <FloatingCards companies={companies} onCardClick={handleCardClick} />

      <div className="relative z-10 flex flex-col items-center text-center">
        <h1 className="max-w-xl font-display text-5xl leading-tight text-primary md:text-6xl">
          You don&apos;t need connections. You need the right founder.
        </h1>

        <div className="mt-10 w-full max-w-2xl">
          <SearchBar
            onSearch={handleSearch}
            onSubmit={handleSubmit}
          />
        </div>
      </div>

      <div className="relative z-10 mt-32 flex flex-col items-center gap-4 pb-16">
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
    </main>
  );
}
