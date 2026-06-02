"use client";

import { useState } from "react";
import { generateEmailDraft, sendEmail, getGmailAuthUrl } from "@/lib/api";

const TONES = [
  { key: "curious", label: "Curious" },
  { key: "friendly", label: "Friendly" },
  { key: "scrappy", label: "Scrappy" },
  { key: "earnest", label: "Earnest" },
] as const;

type ToneKey = (typeof TONES)[number]["key"];

interface EmailWorkspaceProps {
  founderEmail?: string | null;
  emailConfidence?: string | null;
  companyName: string;
  companyId: number;
  founderName?: string | null;
  founderLinkedin?: string | null;
  gmailConnected: boolean;
  hasBio: boolean;
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
  emailConfidence,
  companyName,
  companyId,
  founderName,
  founderLinkedin,
  gmailConnected,
  hasBio,
}: EmailWorkspaceProps) {
  const [body, setBody] = useState("");
  const [originalDraft, setOriginalDraft] = useState("");
  const [subjectLine, setSubjectLine] = useState("");
  const [tone, setTone] = useState<ToneKey>("curious");
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const count = wordCount(body);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      const result = await generateEmailDraft(companyId, tone);
      setBody(result.draft);
      setOriginalDraft(result.draft);
      if (!subjectLine) {
        setSubjectLine(`Quick question - ${companyName}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate draft");
    } finally {
      setGenerating(false);
    }
  }

  async function handleSend() {
    if (!body.trim() || !subjectLine.trim()) return;
    setSending(true);
    setError(null);
    try {
      await sendEmail({
        company_id: companyId,
        subject_line: subjectLine,
        final_text: body,
        original_draft: originalDraft || body,
        tone,
      });
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send email");
    } finally {
      setSending(false);
    }
  }

  async function handleConnectGmail() {
    try {
      const { url } = await getGmailAuthUrl();
      window.location.href = url;
    } catch {
      setError("Failed to get Gmail auth URL");
    }
  }

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

  if (sent) {
    return (
      <div className="space-y-3">
        <h3 className="font-display text-lg text-primary">Email sent</h3>
        <div className="rounded-xl border border-reach-high/30 bg-reach-high/5 px-5 py-4">
          <p className="text-sm text-primary">
            Your email to {founderName || "the founder"} at {companyName} has been sent via Gmail.
            We'll track this in your outreach log and check for replies automatically.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="font-display text-lg text-primary">Write your email</h3>

      {/* Recipient info */}
      {founderEmail ? (
        <div className="rounded-lg border border-card-border bg-card px-4 py-3">
          <p className="text-sm text-primary">
            To: <span className="font-medium">{founderEmail}</span>
          </p>
          {emailConfidence === "medium" && (
            <p className="mt-1 text-xs text-amber-600">
              This email was auto-detected — verify before sending
            </p>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-dashed border-card-border px-4 py-3">
          <p className="text-sm text-secondary">
            Email not available
            {founderLinkedin && (
              <>
                {" — "}
                <a
                  href={founderLinkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent hover:underline"
                >
                  reach out via LinkedIn
                </a>
              </>
            )}
          </p>
        </div>
      )}

      {/* Tone picker */}
      <div className="flex flex-wrap gap-2">
        {TONES.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTone(t.key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              tone === t.key
                ? "bg-accent text-white"
                : "border border-card-border bg-card text-secondary hover:text-primary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Generate button */}
      <div className="relative group inline-block">
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating || !hasBio}
          className="rounded-lg border border-card-border bg-card px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-background disabled:opacity-40"
        >
          {generating ? "Generating..." : "Generate draft"}
        </button>
        {!hasBio && (
          <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 rounded bg-gray-900 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
            Fill in your bio on your profile first
          </span>
        )}
      </div>

      {/* Subject line */}
      <input
        type="text"
        value={subjectLine}
        onChange={(e) => setSubjectLine(e.target.value)}
        placeholder="Subject line"
        className="w-full rounded-lg border border-card-border bg-card px-4 py-2 text-sm text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />

      {/* Email body */}
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Write your email here or generate a draft..."
        rows={8}
        className="w-full resize-y rounded-xl border border-card-border bg-card px-5 py-4 text-sm leading-relaxed text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
      />

      {/* Word count + actions */}
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

          {gmailConnected ? (
            <button
              type="button"
              onClick={handleSend}
              disabled={sending || !body.trim() || !subjectLine.trim() || !founderEmail}
              className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-40"
            >
              {sending ? "Sending..." : "Send via Gmail"}
            </button>
          ) : founderEmail ? (
            <div className="flex items-center gap-2">
              <a
                href={`mailto:${founderEmail}?subject=${encodeURIComponent(subjectLine || `Quick question - ${companyName}`)}&body=${encodeURIComponent(body)}`}
                className="rounded-lg border border-card-border bg-card px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-background"
              >
                Open in email
              </a>
              <button
                type="button"
                onClick={handleConnectGmail}
                className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90"
              >
                Connect Gmail to send
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleConnectGmail}
              className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90"
            >
              Connect Gmail to send
            </button>
          )}
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}
