"use client";

import { useState } from "react";
import {
  TIER1_CATEGORIES,
  TIER2_CAPABILITIES,
  TIER2_LABELS,
  MAX_TIER1,
  MAX_TIER2,
  type Tier1Key,
} from "@/lib/capabilities";

interface CapabilityPickerProps {
  selectedTier1: Tier1Key[];
  selectedTier2: string[];
  onChangeTier1: (categories: Tier1Key[]) => void;
  onChangeTier2: (capabilities: string[]) => void;
}

export default function CapabilityPicker({
  selectedTier1,
  selectedTier2,
  onChangeTier1,
  onChangeTier2,
}: CapabilityPickerProps) {
  const [expanded, setExpanded] = useState<Tier1Key | null>(
    selectedTier1[0] ?? null,
  );

  function toggleTier1(key: Tier1Key) {
    if (selectedTier1.includes(key)) {
      // Deselect category and remove its tier-2 picks
      const nextTier1 = selectedTier1.filter((k) => k !== key);
      const removable = new Set(TIER2_CAPABILITIES[key]);
      const nextTier2 = selectedTier2.filter((c) => !removable.has(c));
      onChangeTier1(nextTier1);
      onChangeTier2(nextTier2);
      if (expanded === key) {
        setExpanded(nextTier1[0] ?? null);
      }
    } else if (selectedTier1.length < MAX_TIER1) {
      onChangeTier1([...selectedTier1, key]);
      setExpanded(key);
    }
  }

  function toggleTier2(cap: string) {
    if (selectedTier2.includes(cap)) {
      onChangeTier2(selectedTier2.filter((c) => c !== cap));
    } else if (selectedTier2.length < MAX_TIER2) {
      onChangeTier2([...selectedTier2, cap]);
    }
  }

  const tier1Keys = Object.keys(TIER1_CATEGORIES) as Tier1Key[];

  return (
    <div className="flex flex-col gap-5">
      {/* Tier 1: Broad categories */}
      <div>
        <p className="mb-2 text-sm font-medium text-secondary">
          What kind of work do you do? Pick up to {MAX_TIER1}.
        </p>
        <div className="flex flex-wrap gap-2">
          {tier1Keys.map((key) => {
            const isSelected = selectedTier1.includes(key);
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggleTier1(key)}
                className={`rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                  isSelected
                    ? "border-accent bg-accent/10 text-accent"
                    : selectedTier1.length >= MAX_TIER1
                      ? "border-card-border bg-card text-tertiary opacity-50"
                      : "border-card-border bg-card text-secondary hover:border-accent/50 hover:text-primary"
                }`}
              >
                {TIER1_CATEGORIES[key]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tier 2: Specific capabilities */}
      {selectedTier1.length > 0 && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-secondary">
              What specifically? Pick up to {MAX_TIER2}.
            </p>
            <p
              className={`text-sm font-medium ${
                selectedTier2.length >= MAX_TIER2
                  ? "text-accent"
                  : "text-tertiary"
              }`}
            >
              {selectedTier2.length} of {MAX_TIER2}
            </p>
          </div>

          {/* Category tabs if 2 selected */}
          {selectedTier1.length > 1 && (
            <div className="mb-3 flex gap-1 rounded-lg bg-background p-1">
              {selectedTier1.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setExpanded(key)}
                  className={`flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    expanded === key
                      ? "bg-card text-primary shadow-sm"
                      : "text-secondary hover:text-primary"
                  }`}
                >
                  {TIER1_CATEGORIES[key]}
                </button>
              ))}
            </div>
          )}

          {/* Capability buttons for expanded category */}
          {expanded && selectedTier1.includes(expanded) && (
            <div className="flex flex-wrap gap-2">
              {TIER2_CAPABILITIES[expanded].map((cap) => {
                const isSelected = selectedTier2.includes(cap);
                const isDisabled =
                  !isSelected && selectedTier2.length >= MAX_TIER2;
                return (
                  <button
                    key={cap}
                    type="button"
                    onClick={() => toggleTier2(cap)}
                    disabled={isDisabled}
                    className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${
                      isSelected
                        ? "border-accent bg-accent text-white"
                        : isDisabled
                          ? "border-card-border bg-card text-tertiary opacity-50"
                          : "border-card-border bg-card text-secondary hover:border-accent/50 hover:text-primary"
                    }`}
                  >
                    {TIER2_LABELS[cap]}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Selected summary */}
      {selectedTier2.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedTier2.map((cap) => (
            <span
              key={cap}
              className="flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-1 text-sm text-white"
            >
              {TIER2_LABELS[cap]}
              <button
                type="button"
                onClick={() => toggleTier2(cap)}
                className="flex h-4 w-4 items-center justify-center rounded-full text-xs leading-none transition-opacity hover:opacity-75"
                aria-label={`Remove ${TIER2_LABELS[cap]}`}
              >
                x
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
