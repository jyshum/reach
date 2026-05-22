"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchCompanies } from "@/lib/api";
import type { CompanyCard as CompanyCardType } from "@/lib/types";
import SearchBar from "@/components/SearchBar";
import FilterBar from "@/components/FilterBar";
import FounderCard from "@/components/FounderCard";
import LoadMoreButton from "@/components/LoadMoreButton";

const PAGE_SIZE = 20;

function FeedContent() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [companies, setCompanies] = useState<CompanyCardType[]>([]);
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [industry, setIndustry] = useState("");
  const [reachability, setReachability] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadCompanies = useCallback(
    async (pageNum: number, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);

      try {
        const data = await fetchCompanies({
          industry: industry || undefined,
          reachability: reachability || undefined,
          page: pageNum,
          limit: PAGE_SIZE,
        });

        if (append) {
          setCompanies((prev) => [...prev, ...data]);
        } else {
          setCompanies(data);
        }
        setHasMore(data.length === PAGE_SIZE);
      } catch {
        setHasMore(false);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [industry, reachability],
  );

  useEffect(() => {
    if (authenticated) {
      setPage(1);
      loadCompanies(1, false);
    }
  }, [authenticated, industry, reachability, loadCompanies]);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadCompanies(nextPage, true);
  };

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  // Client-side filter on search query
  const filtered = searchQuery
    ? companies.filter(
        (c) =>
          c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (c.one_liner &&
            c.one_liner.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (c.industry &&
            c.industry.toLowerCase().includes(searchQuery.toLowerCase())),
      )
    : companies;

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6 flex flex-col items-center gap-4">
        <SearchBar
          onSearch={handleSearch}
          placeholder="Search founders..."
          initialValue={initialQuery}
        />
        <FilterBar
          industry={industry}
          reachability={reachability}
          onIndustryChange={setIndustry}
          onReachabilityChange={setReachability}
        />
      </div>

      {loading ? (
        <div className="py-20 text-center text-secondary">
          Loading founders...
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-20 text-center text-secondary">
          No founders match your search. Try different keywords.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((company) => (
            <FounderCard key={company.id} company={company} />
          ))}
        </div>
      )}

      <LoadMoreButton
        onClick={handleLoadMore}
        loading={loadingMore}
        hasMore={hasMore && !searchQuery}
      />
    </main>
  );
}

export default function FeedPage() {
  return (
    <Suspense>
      <FeedContent />
    </Suspense>
  );
}
