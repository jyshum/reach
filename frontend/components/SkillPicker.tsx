"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type FocusEvent,
  type KeyboardEvent,
} from "react";
import { POPULAR_SKILLS, ALL_SKILLS } from "@/lib/skills";

interface SkillPickerProps {
  selected: string[];
  onChange: (skills: string[]) => void;
  max?: number;
}

function getSuggestions(searchQuery: string, selected: string[]) {
  const query = searchQuery.trim().toLowerCase();
  const source = query ? ALL_SKILLS : POPULAR_SKILLS;

  return source
    .filter((skill) => {
      const matchesQuery = query ? skill.toLowerCase().includes(query) : true;
      return matchesQuery && !selected.includes(skill);
    })
    .slice(0, 12);
}

export default function SkillPicker({
  selected,
  onChange,
  max = 5,
}: SkillPickerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const rootRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();

  const suggestions = useMemo(
    () => getSuggestions(searchQuery, selected),
    [searchQuery, selected]
  );

  const activeSuggestionId =
    open && activeIndex >= 0 && activeIndex < suggestions.length
      ? `${listboxId}-option-${activeIndex}`
      : undefined;

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      const root = rootRef.current;

      if (root && !root.contains(event.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
    };
  }, []);

  function openSuggestions(nextSuggestions = suggestions) {
    setOpen(true);
    setActiveIndex(nextSuggestions.length > 0 ? 0 : -1);
  }

  function closeSuggestions() {
    setOpen(false);
    setActiveIndex(-1);
  }

  function addSkill(skill: string) {
    if (selected.includes(skill)) {
      return;
    }

    onChange([...selected, skill]);
    setSearchQuery("");
    closeSuggestions();
  }

  function removeSkill(skill: string) {
    const nextSelected = selected.filter((s) => s !== skill);
    onChange(nextSelected);

    if (open) {
      const nextSuggestions = getSuggestions(searchQuery, nextSelected);
      setActiveIndex(nextSuggestions.length > 0 ? 0 : -1);
    }
  }

  function handleSearchChange(e: ChangeEvent<HTMLInputElement>) {
    const query = e.target.value;
    const nextSuggestions = getSuggestions(query, selected);

    setSearchQuery(query);
    openSuggestions(nextSuggestions);
  }

  function handleBlur(e: FocusEvent<HTMLDivElement>) {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      closeSuggestions();
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      closeSuggestions();
      return;
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActiveIndex((current) =>
        suggestions.length > 0 ? (current + 1) % suggestions.length : -1
      );
      return;
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      setActiveIndex((current) =>
        suggestions.length > 0
          ? (current - 1 + suggestions.length) % suggestions.length
          : -1
      );
      return;
    }

    if (
      e.key === "Enter" &&
      open &&
      activeIndex >= 0 &&
      activeIndex < suggestions.length
    ) {
      e.preventDefault();
      addSkill(suggestions[activeIndex]);
    }
  }

  const isOverMax = selected.length > max;

  return (
    <div ref={rootRef} onBlur={handleBlur} className="flex flex-col gap-3">
      <div>
        <div className="relative">
          <div className="flex rounded-lg border border-card-border bg-card focus-within:border-accent">
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              onFocus={() => openSuggestions()}
              onKeyDown={handleKeyDown}
              placeholder="Search skills or choose a popular skill"
              className="min-w-0 flex-1 rounded-l-lg bg-transparent px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none"
              role="combobox"
              aria-expanded={open}
              aria-controls={listboxId}
              aria-autocomplete="list"
              aria-activedescendant={activeSuggestionId}
            />
            <button
              type="button"
              onClick={() => {
                if (open) {
                  closeSuggestions();
                } else {
                  openSuggestions();
                }
              }}
              className="flex w-10 items-center justify-center rounded-r-lg border-l border-card-border text-sm text-secondary transition-colors hover:text-primary"
              aria-label="Toggle skill suggestions"
            >
              v
            </button>
          </div>

          {open && (
            <div
              id={listboxId}
              role="listbox"
              className="absolute z-20 mt-2 max-h-72 w-full overflow-y-auto rounded-lg border border-card-border bg-card shadow-lg"
            >
              {suggestions.length > 0 ? (
                suggestions.map((skill, index) => (
                  <button
                    key={skill}
                    id={`${listboxId}-option-${index}`}
                    role="option"
                    aria-selected={index === activeIndex}
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => addSkill(skill)}
                    className={`block w-full px-3 py-2 text-left text-sm transition-colors hover:bg-background hover:text-primary ${
                      index === activeIndex
                        ? "bg-background text-primary"
                        : "text-secondary"
                    }`}
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
