"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type WheelEvent,
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

  const updateProgress = useCallback(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;

    const maxScroll = scroller.scrollWidth - scroller.clientWidth;
    setProgress(maxScroll > 0 ? scroller.scrollLeft / maxScroll : 0);
  }, []);

  useEffect(() => {
    updateProgress();
  }, [companies, updateProgress]);

  const scrollToProgress = useCallback((nextProgress: number) => {
    const scroller = scrollerRef.current;
    if (!scroller) return;

    const maxScroll = scroller.scrollWidth - scroller.clientWidth;
    const clamped = Math.min(Math.max(nextProgress, 0), 1);

    scroller.scrollLeft = maxScroll * clamped;
    setProgress(clamped);
  }, []);

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
    scrollToProgress(progressFromClientX(e.clientX));
  }

  function handleSliderPointerMove(e: PointerEvent<HTMLDivElement>) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    scrollToProgress(progressFromClientX(e.clientX));
  }

  const moveBy = useCallback((amount: number) => {
    const scroller = scrollerRef.current;
    if (!scroller) return false;

    const maxScroll = scroller.scrollWidth - scroller.clientWidth;
    if (maxScroll <= 0) return false;

    const current = scroller.scrollLeft;
    const next = Math.min(Math.max(current + amount, 0), maxScroll);

    if (next === current) return false;

    scroller.scrollLeft = next;
    setProgress(next / maxScroll);
    return true;
  }, []);

  const handleHijackWheel = useCallback(
    (e: globalThis.WheelEvent | WheelEvent<HTMLDivElement>) => {
      const root = rootRef.current;
      const scroller = scrollerRef.current;
      if (!root || !scroller) return;

      const target = e.target as HTMLElement | null;
      if (target?.closest("input, textarea, select")) return;

      const rect = root.getBoundingClientRect();
      const isRailVisible = rect.top < window.innerHeight && rect.bottom > 0;
      if (!isRailVisible) return;

      const maxScroll = scroller.scrollWidth - scroller.clientWidth;
      if (maxScroll <= 0) return;

      const delta =
        Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
      const canMoveRight = delta > 0 && scroller.scrollLeft < maxScroll;
      const canMoveLeft = delta < 0 && scroller.scrollLeft > 0;

      if ((canMoveRight || canMoveLeft) && moveBy(delta)) {
        e.preventDefault();
      }
    },
    [moveBy],
  );

  useEffect(() => {
    window.addEventListener("wheel", handleHijackWheel, {
      passive: false,
      capture: true,
    });

    return () => {
      window.removeEventListener("wheel", handleHijackWheel, {
        capture: true,
      });
    };
  }, [handleHijackWheel]);

  function handleSliderKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const scroller = scrollerRef.current;
    if (!scroller) return;

    const maxScroll = scroller.scrollWidth - scroller.clientWidth;
    const step = scroller.clientWidth * 0.18;
    let handled = true;

    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      moveBy(step);
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      moveBy(-step);
    } else if (e.key === "Home") {
      scroller.scrollLeft = 0;
      setProgress(0);
    } else if (e.key === "End") {
      scroller.scrollLeft = maxScroll;
      setProgress(1);
    } else {
      handled = false;
    }

    if (handled) {
      e.preventDefault();
    }
  }

  return (
    <div ref={rootRef} className="w-full pb-4" onWheel={handleHijackWheel}>
      <div
        ref={scrollerRef}
        onScroll={updateProgress}
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
  );
}
