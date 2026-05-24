"use client";

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
  return (
    <div className="w-full overflow-x-auto pb-4">
      <div className="mx-auto flex w-max max-w-none snap-x gap-4 px-6 sm:gap-5 lg:px-10">
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
    </div>
  );
}
