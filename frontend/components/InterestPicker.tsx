"use client";

import { useEffect, useState } from "react";
import { fetchInterests, type InterestCategory } from "@/lib/api";

interface InterestPickerProps {
  selected: string[];
  onChange: (interests: string[]) => void;
  maxSelections?: number;
}

export default function InterestPicker({
  selected,
  onChange,
  maxSelections = 2,
}: InterestPickerProps) {
  const [categories, setCategories] = useState<InterestCategory[]>([]);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  useEffect(() => {
    fetchInterests().then(setCategories).catch(() => {});
  }, []);

  function toggleTag(tag: string) {
    if (selected.includes(tag)) {
      onChange(selected.filter((t) => t !== tag));
    } else if (selected.length < maxSelections) {
      onChange([...selected, tag]);
    }
  }

  function toggleCategory(name: string) {
    setExpandedCategory(expandedCategory === name ? null : name);
  }

  function categoryHasSelection(cat: InterestCategory): boolean {
    return cat.tags.some((t) => selected.includes(t));
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-neutral-500">
        Pick up to {maxSelections} domains that excite you
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {categories.map((cat) => (
          <div key={cat.name}>
            <button
              onClick={() => toggleCategory(cat.name)}
              className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                expandedCategory === cat.name
                  ? "border-teal-500 bg-teal-50 text-teal-800"
                  : categoryHasSelection(cat)
                    ? "border-teal-300 bg-teal-50/50"
                    : "border-neutral-200 hover:border-neutral-300"
              }`}
            >
              {cat.name}
              {categoryHasSelection(cat) && (
                <span className="ml-1 text-teal-600">
                  ({cat.tags.filter((t) => selected.includes(t)).length})
                </span>
              )}
            </button>
            {expandedCategory === cat.name && (
              <div className="mt-1 flex flex-wrap gap-1 pl-1">
                {cat.tags.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    disabled={
                      !selected.includes(tag) && selected.length >= maxSelections
                    }
                    className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                      selected.includes(tag)
                        ? "bg-teal-600 text-white"
                        : selected.length >= maxSelections
                          ? "bg-neutral-100 text-neutral-400 cursor-not-allowed"
                          : "bg-neutral-100 text-neutral-700 hover:bg-neutral-200"
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2.5 py-1 text-xs text-teal-800"
            >
              {tag}
              <button
                onClick={() => onChange(selected.filter((t) => t !== tag))}
                className="ml-0.5 text-teal-600 hover:text-teal-900"
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
