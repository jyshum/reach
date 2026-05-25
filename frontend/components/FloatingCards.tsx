"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
} from "react";
import type { CompanyCard } from "@/lib/types";
import FounderCard from "@/components/FounderCard";

interface FloatingCardsProps {
  companies: CompanyCard[];
  onCardClick?: (company: CompanyCard) => void;
}

export default function FloatingCards({
  companies,
  onCardClick,
}: FloatingCardsProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const sliderRef = useRef<HTMLDivElement>(null);
  const [progress, setProgress] = useState(0);

  const applyProgress = useCallback((nextProgress: number) => {
    const scroller = scrollerRef.current;
    if (!scroller) return;

    const maxScroll = scroller.scrollWidth - scroller.clientWidth;
    const clamped = Math.min(Math.max(nextProgress, 0), 1);
    scroller.scrollLeft = maxScroll * clamped;
    setProgress(clamped);
  }, []);

  const syncToWindowScroll = useCallback(() => {
    const root = rootRef.current;
    if (!root) return;

    const rect = root.getBoundingClientRect();
    const scrollableDistance = root.offsetHeight - window.innerHeight;

    if (scrollableDistance <= 0) {
      applyProgress(0);
      return;
    }

    const scrolledThroughSection = Math.min(
      Math.max(-rect.top, 0),
      scrollableDistance,
    );

    applyProgress(scrolledThroughSection / scrollableDistance);
  }, [applyProgress]);

  useEffect(() => {
    syncToWindowScroll();

    window.addEventListener("scroll", syncToWindowScroll, { passive: true });
    window.addEventListener("resize", syncToWindowScroll);

    return () => {
      window.removeEventListener("scroll", syncToWindowScroll);
      window.removeEventListener("resize", syncToWindowScroll);
    };
  }, [companies, syncToWindowScroll]);

  function scrollPageToProgress(nextProgress: number) {
    const root = rootRef.current;
    if (!root) return;

    const rect = root.getBoundingClientRect();
    const sectionTop = window.scrollY + rect.top;
    const scrollableDistance = root.offsetHeight - window.innerHeight;

    window.scrollTo({
      top: sectionTop + scrollableDistance * nextProgress,
      behavior: "auto",
    });
  }

  function progressFromClientX(clientX: number) {
    const slider = sliderRef.current;
    if (!slider) return progress;

    const rect = slider.getBoundingClientRect();
    return Math.min(
      Math.max((clientX - rect.left) / rect.width, 0),
      1,
    );
  }

  function handleSliderPointerDown(e: PointerEvent<HTMLDivElement>) {
    e.currentTarget.setPointerCapture(e.pointerId);
    scrollPageToProgress(progressFromClientX(e.clientX));
  }

  function handleSliderPointerMove(e: PointerEvent<HTMLDivElement>) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    scrollPageToProgress(progressFromClientX(e.clientX));
  }

  function handleSliderKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const step = 0.08;
    let handled = false;
    let nextProgress = progress;

    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      nextProgress = Math.min(progress + step, 1);
      handled = true;
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      nextProgress = Math.max(progress - step, 0);
      handled = true;
    } else if (e.key === "Home") {
      nextProgress = 0;
      handled = true;
    } else if (e.key === "End") {
      nextProgress = 1;
      handled = true;
    }

    if (handled) {
      e.preventDefault();
      scrollPageToProgress(nextProgress);
    }
  }

  return (
    <section ref={rootRef} className="relative h-[180vh] w-full">
      <div className="sticky top-28 w-full pb-4">
        <div
          ref={scrollerRef}
          className="scrollbar-hide mx-auto flex w-full max-w-none snap-x gap-4 overflow-x-hidden px-6 sm:gap-5 lg:px-10"
        >
          {companies.slice(0, 20).map((company) => (
            <div
              key={company.id}
              className="w-[min(82vw,24rem)] flex-none snap-start sm:w-[26rem]"
            >
              <FounderCard
                company={company}
                onClick={() => onCardClick?.(company)}
              />
            </div>
          ))}
        </div>

        <div className="mx-auto mt-6 w-[min(36rem,72vw)]">
          <div
            ref={sliderRef}
            role="slider"
            aria-label="Founder preview position"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(progress * 100)}
            tabIndex={0}
            onPointerDown={handleSliderPointerDown}
            onPointerMove={handleSliderPointerMove}
            onKeyDown={handleSliderKeyDown}
            className="relative h-2 cursor-pointer rounded-full bg-card-border/70 outline-none ring-accent/20 transition-shadow focus:ring-4"
          >
            <div
              className="h-full rounded-full bg-accent"
              style={{ width: `${progress * 100}%` }}
            />
            <div
              className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-accent shadow-card"
              style={{ left: `${progress * 100}%` }}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
