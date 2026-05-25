"use client";

import { useState, useEffect, useRef } from "react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  onSubmit?: (query: string) => void;
  placeholder?: string;
  debounceMs?: number;
  initialValue?: string;
  size?: "default" | "large";
}

export default function SearchBar({
  onSearch,
  onSubmit,
  placeholder = "Cold email the founders who actually respond",
  debounceMs = 300,
  initialValue = "",
  size = "default",
}: SearchBarProps) {
  const [value, setValue] = useState(initialValue);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const sizeClasses =
    size === "large" ? "px-6 py-4 text-base md:text-lg" : "px-4 py-3 text-sm";

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      onSearch(value);
    }, debounceMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [value, debounceMs, onSearch]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && onSubmit) {
      onSubmit(value);
    }
  };

  return (
    <div className="w-full">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className={`w-full rounded-xl border border-card-border bg-card ${sizeClasses} text-primary shadow-card placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20`}
      />
    </div>
  );
}
