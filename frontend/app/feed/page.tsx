"use client";

import { useState, useEffect, useCallback, Suspense, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchCompanies } from "@/lib/api";
import type { CompanyCard as CompanyCardType } from "@/lib/types";
import SearchBar from "@/components/SearchBar";
import FilterBar from "@/components/FilterBar";
import FounderCard from "@/components/FounderCard";
import LoadMoreButton from "@/components/LoadMoreButton";
import SkeletonCard from "@/components/SkeletonCard";

const PAGE_SIZE = 20;

const filterKey = (industry: string, reachability: string, search: string) =>
  `${industry}\u0000${reachability}\u0000${search}`;

function FeedContent() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [companies, setCompanies] = useState<CompanyCardType[]>([]);
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [industry, setIndustry] = useState("");
  const [reachability, setReachability] = useState("");
  const pageRef = useRef(1);
  const requestSeqRef = useRef(0);
  const filterRef = useRef({ industry: "", reachability: "", search: "" });
  const activeResultsFilterKeyRef = useRef("");
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    filterRef.current = { industry, reachability, search: searchQuery };
  }, [industry, reachability, searchQuery]);

  const loadCompanies = useCallback(
    async (pageNum: number, append: boolean) => {
      const requestSeq = ++requestSeqRef.current;
      const requestIndustry = industry;
      const requestReachability = reachability;
      const requestSearch = searchQuery;
      const requestPageNum = pageNum;
      const requestAppend = append;
      const requestFilterKey = filterKey(requestIndustry, requestReachability, requestSearch);

      if (requestSeq !== requestSeqRef.current) return;

      if (requestAppend) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setLoadingMore(false);
      }

      try {
        const data = await fetchCompanies({
          industry: requestIndustry || undefined,
          reachability: requestReachability || undefined,
          search: requestSearch.trim() || undefined,
          page: requestPageNum,
          limit: PAGE_SIZE,
        });

        const currentFilterKey = filterKey(
          filterRef.current.industry,
          filterRef.current.reachability,
          filterRef.current.search,
        );
        const isCurrentRequest = requestSeq === requestSeqRef.current;
        const filterStillMatches = requestFilterKey === currentFilterKey;

        if (!isCurrentRequest || !filterStillMatches) return;

        if (requestAppend) {
          if (
            activeResultsFilterKeyRef.current !== requestFilterKey ||
            pageRef.current !== requestPageNum
          ) {
            return;
          }

          setCompanies((prev) => [...prev, ...data]);
        } else {
          activeResultsFilterKeyRef.current = requestFilterKey;
          setCompanies(data);
        }
        setHasMore(data.length === PAGE_SIZE);
      } catch {
        const currentFilterKey = filterKey(
          filterRef.current.industry,
          filterRef.current.reachability,
          filterRef.current.search,
        );

        if (
          requestSeq === requestSeqRef.current &&
          requestFilterKey === currentFilterKey
        ) {
          setHasMore(false);
        }
      } finally {
        const currentFilterKey = filterKey(
          filterRef.current.industry,
          filterRef.current.reachability,
          filterRef.current.search,
        );

        if (
          requestSeq === requestSeqRef.current &&
          requestFilterKey === currentFilterKey
        ) {
          if (requestAppend) setLoadingMore(false);
          else setLoading(false);
        }
      }
    },
    [industry, reachability, searchQuery],
  );

  useEffect(() => {
    if (!authenticated) return;

    const requestSeq = ++requestSeqRef.current;
    const requestIndustry = industry;
    const requestReachability = reachability;
    const requestSearch = searchQuery;
    const requestPageNum = 1;
    const requestFilterKey = filterKey(requestIndustry, requestReachability, requestSearch);

    pageRef.current = requestPageNum;

    async function loadFirstPage() {
      try {
        const data = await fetchCompanies({
          industry: requestIndustry || undefined,
          reachability: requestReachability || undefined,
          search: requestSearch.trim() || undefined,
          page: requestPageNum,
          limit: PAGE_SIZE,
        });

        const currentFilterKey = filterKey(
          filterRef.current.industry,
          filterRef.current.reachability,
          filterRef.current.search,
        );

        if (
          requestSeq !== requestSeqRef.current ||
          requestFilterKey !== currentFilterKey
        ) {
          return;
        }

        activeResultsFilterKeyRef.current = requestFilterKey;
        setCompanies(data);
        setHasMore(data.length === PAGE_SIZE);
      } catch {
        const currentFilterKey = filterKey(
          filterRef.current.industry,
          filterRef.current.reachability,
          filterRef.current.search,
        );

        if (
          requestSeq === requestSeqRef.current &&
          requestFilterKey === currentFilterKey
        ) {
          setHasMore(false);
        }
      } finally {
        const currentFilterKey = filterKey(
          filterRef.current.industry,
          filterRef.current.reachability,
          filterRef.current.search,
        );

        if (
          requestSeq === requestSeqRef.current &&
          requestFilterKey === currentFilterKey
        ) {
          setLoading(false);
        }
      }
    }

    void loadFirstPage();
  }, [authenticated, industry, reachability, searchQuery]);

  const handleLoadMore = () => {
    if (loading || loadingMore || !hasMore) return;

    const nextPage = pageRef.current + 1;
    pageRef.current = nextPage;
    loadCompanies(nextPage, true);
  };

  const handleSearch = useCallback((query: string) => {
    pageRef.current = 1;
    setLoading(true);
    setLoadingMore(false);
    setSearchQuery(query);
  }, []);

  const handleIndustryChange = useCallback((value: string) => {
    pageRef.current = 1;
    setLoading(true);
    setLoadingMore(false);
    setIndustry(value);
  }, []);

  const handleReachabilityChange = useCallback((value: string) => {
    pageRef.current = 1;
    setLoading(true);
    setLoadingMore(false);
    setReachability(value);
  }, []);

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <main className="page-enter mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6 flex flex-col items-center gap-4">
        <SearchBar
          onSearch={handleSearch}
          placeholder="Search by startup name or founder name..."
          initialValue={initialQuery}
        />
        <FilterBar
          industry={industry}
          reachability={reachability}
          onIndustryChange={handleIndustryChange}
          onReachabilityChange={handleReachabilityChange}
        />
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : companies.length === 0 ? (
        <div className="py-20 text-center text-secondary">
          No startups match that search yet. Try a skill, industry, or product
          area.
        </div>
      ) : (
        <div className="space-y-3">
          {companies.map((company) => (
            <FounderCard key={company.id} company={company} />
          ))}
        </div>
      )}

      <LoadMoreButton
        onClick={handleLoadMore}
        loading={loadingMore}
        hasMore={hasMore && !loading}
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
