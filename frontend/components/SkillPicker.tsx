"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
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
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const suggestions = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const source = query ? ALL_SKILLS : POPULAR_SKILLS;

    return source
      .filter((skill) => {
        const matchesQuery = query
          ? skill.toLowerCase().includes(query)
          : true;
        return matchesQuery && !selected.includes(skill);
      })
      .slice(0, 12);
  }, [searchQuery, selected]);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      const root = rootRef.current;

      if (root && !root.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, []);

  function addSkill(skill: string) {
    if (selected.includes(skill)) {
      return;
    }

    onChange([...selected, skill]);
    setSearchQuery("");
    setOpen(false);
  }

  function removeSkill(skill: string) {
    onChange(selected.filter((s) => s !== skill));
  }

  function handleSearchChange(e: ChangeEvent<HTMLInputElement>) {
    setSearchQuery(e.target.value);
    setOpen(true);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      setOpen(false);
      return;
    }

    if (e.key === "Enter" && suggestions.length > 0) {
      e.preventDefault();
      addSkill(suggestions[0]);
    }
  }

  const isOverMax = selected.length > max;

  return (
    <div ref={rootRef} className="flex flex-col gap-3">
      <div>
        <div className="relative">
          <div className="flex rounded-lg border border-card-border bg-card focus-within:border-accent">
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => setOpen(true)}
              onKeyDown={handleKeyDown}
              placeholder="Search skills or choose a popular skill"
              className="min-w-0 flex-1 rounded-l-lg bg-transparent px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setOpen((current) => !current)}
              className="flex w-10 items-center justify-center rounded-r-lg border-l border-card-border text-sm text-secondary transition-colors hover:text-primary"
              aria-label="Toggle skill suggestions"
            >
              v
            </button>
          </div>

          {open && (
            <div
              className="absolute z-20 mt-2 max-h-72 w-full overflow-y-auto rounded-lg border border-card-border bg-card shadow-lg"
            >
              {suggestions.length > 0 ? (
                suggestions.map((skill) => (
                  <button
                    key={skill}
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => addSkill(skill)}
                    className="block w-full px-3 py-2 text-left text-sm text-secondary transition-colors hover:bg-background hover:text-primary"
                  >
                    {skill}
                  </button>
                ))
              ) : (
                <p className="px-3 py-2 text-sm text-tertiary">
                  No matching skills
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      <div>
        <p
          className={`mb-2 text-sm font-medium ${
            isOverMax ? "text-reach-med" : "text-secondary"
          }`}
        >
          {selected.length} of {max} selected
        </p>
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {selected.map((skill) => (
              <span
                key={skill}
                className="flex items-center gap-1.5 rounded-full bg-accent px-2.5 py-1 text-sm text-white"
              >
                {skill}
                <button
                  type="button"
                  onClick={() => removeSkill(skill)}
                  className="flex h-4 w-4 items-center justify-center rounded-full text-xs leading-none transition-opacity hover:opacity-75"
                  aria-label={`Remove ${skill}`}
                >
                  x
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
