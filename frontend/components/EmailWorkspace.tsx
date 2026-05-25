"use client";

import { useState } from "react";

interface EmailWorkspaceProps {
  founderEmail?: string | null;
  companyName: string;
}

function wordCount(text: string): number {
  return text.trim() === "" ? 0 : text.trim().split(/\s+/).length;
}

function countColor(count: number): string {
  if (count >= 150) return "text-red-500";
  if (count >= 120) return "text-reach-med";
  return "text-tertiary";
}

export default function EmailWorkspace({
  founderEmail,
  companyName,
}: EmailWorkspaceProps) {
  const [body, setBody] = useState("");
  const [copied, setCopied] = useState(false);
  const count = wordCount(body);

  const mailtoHref = founderEmail
    ? `mailto:${founderEmail}?subject=${encodeURIComponent(`Quick question - ${companyName}`)}&body=${encodeURIComponent(body)}`
    : undefined;

  async function handleCopy() {
    if (!body.trim() || !navigator.clipboard) return;

    try {
      await navigator.clipboard.writeText(body);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="space-y-3">
      <h3 className="font-display text-lg text-primary">Write your email</h3>

      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Write your email here..."
        rows={8}
        className="w-full resize-y rounded-xl border border-card-border bg-card px-5 py-4 text-sm leading-relaxed text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className={`text-sm ${countColor(count)}`}>
          {count} word{count !== 1 ? "s" : ""}{" "}
          <span className="text-tertiary">· Aim for under 150 words</span>
        </p>

        <div className="flex flex-wrap items-center gap-2 sm:justify-end">
          <button
            type="button"
            onClick={handleCopy}
            disabled={!body.trim()}
            className="rounded-lg border border-card-border bg-card px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-background disabled:cursor-not-allowed disabled:opacity-40"
          >
            {copied ? "Copied" : "Copy draft"}
          </button>

          {founderEmail ? (
            <a
              href={mailtoHref}
              className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90"
            >
              Open email
            </a>
          ) : (
            <span className="text-sm text-tertiary">
              Email not available yet
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
