"use client";

import { useState, useRef } from "react";
import { POPULAR_SKILLS, ALL_SKILLS } from "@/lib/skills";

interface SkillPickerProps {
  selected: string[];
  onChange: (skills: string[]) => void;
  max?: number;
}

export default function SkillPicker({
  selected,
  onChange,
  max = 5,
}: SkillPickerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<string[]>([]);
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  function toggleSkill(skill: string) {
    if (selected.includes(skill)) {
      onChange(selected.filter((s) => s !== skill));
    } else {
      onChange([...selected, skill]);
    }
  }

  function removeSkill(skill: string) {
    onChange(selected.filter((s) => s !== skill));
  }

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    const query = e.target.value;
    setSearchQuery(query);

    if (debounceTimer.current !== undefined) {
      clearTimeout(debounceTimer.current);
    }

    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    debounceTimer.current = setTimeout(() => {
      const lower = query.toLowerCase();
      const results = ALL_SKILLS.filter(
        (skill) =>
          skill.toLowerCase().includes(lower) && !selected.includes(skill)
      ).slice(0, 20);
      setSearchResults(results);
    }, 300);
  }

  const isOverMax = selected.length > max;

  return (
    <div className="flex flex-col gap-4">
      {/* Popular Skills */}
      <div>
        <p className="mb-2 text-sm font-medium text-secondary">
          Popular skills
        </p>
        <div className="flex flex-wrap gap-2">
          {POPULAR_SKILLS.map((skill) => {
            const isSelected = selected.includes(skill);
            return (
              <button
                key={skill}
                type="button"
                onClick={() => toggleSkill(skill)}
                className={`rounded-full px-3 py-1 text-sm transition-colors ${
                  isSelected
                    ? "bg-accent text-white"
                    : "border border-card-border bg-card text-secondary hover:text-primary"
                }`}
              >
                {skill}
              </button>
            );
          })}
        </div>
      </div>

      {/* Search */}
      <div>
        <input
          type="text"
          value={searchQuery}
          onChange={handleSearchChange}
          placeholder="Search for more skills..."
          className="w-full rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:border-accent focus:outline-none"
        />
        {searchResults.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {searchResults.map((skill) => (
              <button
                key={skill}
                type="button"
                onClick={() => {
                  toggleSkill(skill);
                  setSearchQuery("");
                  setSearchResults([]);
                }}
                className="rounded-full border border-card-border bg-card px-3 py-1 text-sm text-secondary hover:text-primary transition-colors"
              >
                {skill}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected Skills */}
      {selected.length > 0 && (
        <div>
          <p
            className={`mb-2 text-sm font-medium ${
              isOverMax ? "text-reach-med" : "text-secondary"
            }`}
          >
            {selected.length} of {max} selected
          </p>
          <div className="flex flex-wrap gap-2">
            {selected.map((skill) => (
              <span
                key={skill}
                className="flex items-center gap-1.5 rounded-full bg-accent px-3 py-1 text-sm text-white"
              >
                {skill}
                <button
                  type="button"
                  onClick={() => removeSkill(skill)}
                  className="flex items-center justify-center rounded-full hover:opacity-75 transition-opacity"
                  aria-label={`Remove ${skill}`}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
