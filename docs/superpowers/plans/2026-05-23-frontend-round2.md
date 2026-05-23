# Frontend Round 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add skill-selection onboarding, profile editing, and outreach tracker to the REACH frontend.

**Architecture:** Three new pages (`/onboard`, `/profile`, `/tracker`) plus modifications to existing brief page, navbar, auth form, and API client. Four new shared components (SkillPicker, OutreachForm, OutreachRow, StatsHeader). Skills data generated from enriched companies and bundled as a static import.

**Tech Stack:** Next.js 16 (App Router), Tailwind v4 (@theme inline), Supabase Auth JS, TypeScript

**Spec:** `docs/superpowers/specs/2026-05-23-frontend-round2-design.md`

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `frontend/lib/skills.ts` | Top 30 popular skills + full tag list for search |
| Create | `frontend/lib/generate-skills.ts` | Script to generate skills.ts from enriched data |
| Modify | `frontend/lib/api.ts` | Add fetchProfile, updateProfile, fetchOutreach, createOutreach, updateOutreach |
| Modify | `frontend/lib/types.ts` | Add OutreachEntry interface |
| Create | `frontend/components/SkillPicker.tsx` | Skill chip grid + search + selected display |
| Create | `frontend/components/OutreachForm.tsx` | Inline form to log new outreach |
| Create | `frontend/components/OutreachRow.tsx` | Single outreach entry with editable status |
| Create | `frontend/components/StatsHeader.tsx` | Three count boxes + follow-up banner |
| Modify | `frontend/components/Navbar.tsx` | Add Tracker + Profile links for authenticated users |
| Modify | `frontend/components/AuthForm.tsx` | Signup redirects to /onboard instead of /feed |
| Create | `frontend/app/onboard/page.tsx` | Skill selection onboarding page |
| Create | `frontend/app/profile/page.tsx` | Profile editing page |
| Create | `frontend/app/tracker/page.tsx` | Outreach tracker page |
| Modify | `frontend/app/founder/[id]/page.tsx` | Add outreach section below email workspace |

---

### Task 1: Generate Skills Data + Add Types

**Files:**
- Create: `frontend/lib/skills.ts`
- Modify: `frontend/lib/types.ts`

- [ ] **Step 1: Generate the skills data file**

Run this from the repo root to generate the skills file:

```bash
python3.12 -c "
import json
from collections import Counter

d = json.load(open('data/enriched_companies.json'))
c = Counter()
for co in d:
    for tag in co.get('need_tags', []):
        c[tag] += 1

top30 = [t for t, _ in c.most_common(30)]
all_tags = sorted(c.keys())

print('export const POPULAR_SKILLS = [')
for t in top30:
    print(f'  \"{t}\",')
print('] as const;')
print()
print('export const ALL_SKILLS: string[] = [')
for t in all_tags:
    escaped = t.replace('\"', '\\\\\"')
    print(f'  \"{escaped}\",')
print('];')
" > frontend/lib/skills.ts
```

Verify the file was created and has content:

```bash
head -5 frontend/lib/skills.ts
wc -l frontend/lib/skills.ts
```

Expected: file starts with `export const POPULAR_SKILLS = [` and has ~3200 lines.

- [ ] **Step 2: Add OutreachEntry type to types.ts**

Add to the end of `frontend/lib/types.ts`, before the `INDUSTRIES` constant:

```typescript
export interface OutreachEntry {
  id: number;
  company_id: number;
  company_name: string | null;
  status: "sent" | "replied" | "meeting" | "no-response";
  sent_at: string | null;
  followup_date: string | null;
  notes: string | null;
  created_at: string | null;
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/skills.ts frontend/lib/types.ts
git commit -m "feat: add skills data and OutreachEntry type"
```

---

### Task 2: Extend API Client

**Files:**
- Modify: `frontend/lib/api.ts`

- [ ] **Step 1: Add new API functions**

Read `frontend/lib/api.ts` first. Then add these functions at the end of the file:

```typescript
import type { CompanyCard, CompanyBrief, UserProfile, OutreachEntry } from "./types";
```

(Update the existing import at the top to include `UserProfile` and `OutreachEntry`.)

Add these functions after the existing `fetchBrief`:

```typescript
export async function fetchProfile(): Promise<UserProfile> {
  return apiFetch<UserProfile>("/me");
}

export async function updateProfile(
  data: Partial<{
    skills: string[];
    school: string | null;
    grad_year: number | null;
    bio: string | null;
    github_url: string | null;
    portfolio_url: string | null;
  }>,
): Promise<UserProfile> {
  return apiFetch<UserProfile>("/me", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function fetchOutreach(): Promise<OutreachEntry[]> {
  return apiFetch<OutreachEntry[]>("/outreach");
}

export async function createOutreach(data: {
  company_id: number;
  status: string;
  notes?: string | null;
  sent_at?: string | null;
}): Promise<OutreachEntry> {
  return apiFetch<OutreachEntry>("/outreach", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateOutreach(
  id: number,
  data: { status?: string; notes?: string },
): Promise<OutreachEntry> {
  return apiFetch<OutreachEntry>(`/outreach/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat: add profile and outreach API functions"
```

---

### Task 3: SkillPicker Component

**Files:**
- Create: `frontend/components/SkillPicker.tsx`

- [ ] **Step 1: Create SkillPicker component**

Create `frontend/components/SkillPicker.tsx`:

```tsx
"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<string[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (!search.trim()) {
      setResults([]);
      return;
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      const q = search.toLowerCase();
      const matches = ALL_SKILLS.filter(
        (s) => s.toLowerCase().includes(q) && !selected.includes(s),
      ).slice(0, 20);
      setResults(matches);
    }, 300);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [search, selected]);

  const toggle = useCallback(
    (skill: string) => {
      if (selected.includes(skill)) {
        onChange(selected.filter((s) => s !== skill));
      } else {
        onChange([...selected, skill]);
      }
    },
    [selected, onChange],
  );

  const remove = useCallback(
    (skill: string) => {
      onChange(selected.filter((s) => s !== skill));
    },
    [selected, onChange],
  );

  return (
    <div className="space-y-6">
      {/* Popular skills */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-secondary">
          Popular skills
        </h3>
        <div className="flex flex-wrap gap-2">
          {POPULAR_SKILLS.map((skill) => (
            <button
              key={skill}
              onClick={() => toggle(skill)}
              className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                selected.includes(skill)
                  ? "bg-accent text-white"
                  : "border border-card-border bg-card text-secondary hover:text-primary"
              }`}
            >
              {skill}
            </button>
          ))}
        </div>
      </div>

      {/* Search */}
      <div>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search for more skills..."
          className="w-full rounded-lg border border-card-border bg-card px-4 py-3 text-sm text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
        {results.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {results.map((skill) => (
              <button
                key={skill}
                onClick={() => toggle(skill)}
                className="rounded-lg border border-card-border bg-card px-3 py-1.5 text-sm text-secondary hover:text-primary"
              >
                {skill}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected */}
      {selected.length > 0 && (
        <div>
          <p
            className={`mb-2 text-sm ${
              selected.length > max ? "text-reach-med" : "text-secondary"
            }`}
          >
            {selected.length} of {max} selected
          </p>
          <div className="flex flex-wrap gap-2">
            {selected.map((skill) => (
              <span
                key={skill}
                className="flex items-center gap-1.5 rounded-lg bg-accent/10 px-3 py-1.5 text-sm text-accent"
              >
                {skill}
                <button
                  onClick={() => remove(skill)}
                  className="text-accent/60 hover:text-accent"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/SkillPicker.tsx
git commit -m "feat: add SkillPicker component — popular chips, search, selected display"
```

---

### Task 4: Onboarding Page

**Files:**
- Create: `frontend/app/onboard/page.tsx`

- [ ] **Step 1: Create onboarding page**

Create `frontend/app/onboard/page.tsx`:

```tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchProfile, updateProfile } from "@/lib/api";
import SkillPicker from "@/components/SkillPicker";

export default function OnboardPage() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const router = useRouter();
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [checkingProfile, setCheckingProfile] = useState(true);

  // If user already has skills, skip onboarding
  useEffect(() => {
    if (!authenticated) return;
    fetchProfile()
      .then((profile) => {
        if (profile.skills && profile.skills.length > 0) {
          router.replace("/feed");
        } else {
          setCheckingProfile(false);
        }
      })
      .catch(() => setCheckingProfile(false));
  }, [authenticated, router]);

  const handleContinue = async () => {
    setSaving(true);
    try {
      await updateProfile({ skills: selected });
      router.push("/feed");
    } catch {
      setSaving(false);
    }
  };

  const handleSkip = () => {
    router.push("/feed");
  };

  const handleChange = useCallback((skills: string[]) => {
    setSelected(skills);
  }, []);

  if (authLoading || checkingProfile) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <div className="text-center">
        <h1 className="font-display text-4xl text-primary">
          What are you good at?
        </h1>
        <p className="mt-3 text-secondary">
          Pick 3-5 skills so we can match you with the right founders.
        </p>
      </div>

      <div className="mt-10">
        <SkillPicker selected={selected} onChange={handleChange} />
      </div>

      <div className="mt-10 flex flex-col items-center gap-3">
        <button
          onClick={handleContinue}
          disabled={selected.length < 3 || saving}
          className="rounded-lg bg-accent px-8 py-3 font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Continue"}
        </button>
        <button
          onClick={handleSkip}
          className="text-sm text-tertiary hover:text-secondary"
        >
          Skip for now
        </button>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/onboard/
git commit -m "feat: add onboarding page — skill selection before first feed visit"
```

---

### Task 5: Update AuthForm + Navbar

**Files:**
- Modify: `frontend/components/AuthForm.tsx`
- Modify: `frontend/components/Navbar.tsx`

- [ ] **Step 1: Update AuthForm to redirect signup to /onboard**

Read `frontend/components/AuthForm.tsx`. Change the redirect after successful auth. Replace:

```typescript
      const q = searchParams.get("q");
      router.push(q ? `/feed?q=${encodeURIComponent(q)}` : "/feed");
```

With:

```typescript
      const q = searchParams.get("q");
      if (mode === "signup") {
        router.push("/onboard");
      } else {
        router.push(q ? `/feed?q=${encodeURIComponent(q)}` : "/feed");
      }
```

- [ ] **Step 2: Update Navbar with Tracker and Profile links**

Read `frontend/components/Navbar.tsx`. Replace the authenticated links section. Change:

```tsx
            {session ? (
              <>
                <Link
                  href="/feed"
                  className="text-sm text-secondary hover:text-primary"
                >
                  Feed
                </Link>
                <button
                  onClick={handleSignOut}
                  className="text-sm text-secondary hover:text-primary"
                >
                  Sign out
                </button>
              </>
```

To:

```tsx
            {session ? (
              <>
                <Link
                  href="/feed"
                  className="text-sm text-secondary hover:text-primary"
                >
                  Feed
                </Link>
                <Link
                  href="/tracker"
                  className="text-sm text-secondary hover:text-primary"
                >
                  Tracker
                </Link>
                <Link
                  href="/profile"
                  className="text-sm text-secondary hover:text-primary"
                >
                  Profile
                </Link>
                <button
                  onClick={handleSignOut}
                  className="text-sm text-secondary hover:text-primary"
                >
                  Sign out
                </button>
              </>
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/AuthForm.tsx frontend/components/Navbar.tsx
git commit -m "feat: signup redirects to onboard, navbar adds Tracker + Profile links"
```

---

### Task 6: Profile Page

**Files:**
- Create: `frontend/app/profile/page.tsx`

- [ ] **Step 1: Create profile page**

Create `frontend/app/profile/page.tsx`:

```tsx
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchProfile, updateProfile } from "@/lib/api";
import type { UserProfile } from "@/lib/types";
import SkillPicker from "@/components/SkillPicker";

export default function ProfilePage() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Form state
  const [school, setSchool] = useState("");
  const [gradYear, setGradYear] = useState("");
  const [bio, setBio] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");

  // Skill auto-save timer
  const skillTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (!authenticated) return;
    fetchProfile()
      .then((p) => {
        setProfile(p);
        setSchool(p.school || "");
        setGradYear(p.grad_year ? String(p.grad_year) : "");
        setBio(p.bio || "");
        setGithubUrl(p.github_url || "");
        setPortfolioUrl(p.portfolio_url || "");
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [authenticated]);

  const handleSkillsChange = useCallback(
    (skills: string[]) => {
      setProfile((prev) => (prev ? { ...prev, skills } : prev));
      // Debounced auto-save
      if (skillTimerRef.current) clearTimeout(skillTimerRef.current);
      skillTimerRef.current = setTimeout(() => {
        updateProfile({ skills }).catch(() => {});
      }, 500);
    },
    [],
  );

  const handleSaveDetails = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await updateProfile({
        school: school || null,
        grad_year: gradYear ? Number(gradYear) : null,
        bio: bio || null,
        github_url: githubUrl || null,
        portfolio_url: portfolioUrl || null,
      });
      setProfile(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-8">
      <h1 className="font-display text-3xl text-primary">Profile</h1>

      {/* Account info */}
      <div className="mt-4 flex items-center gap-3">
        <p className="text-sm text-secondary">{profile?.email}</p>
        <span className="rounded bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
          {profile?.tier || "free"}
        </span>
      </div>
      {profile?.tier === "free" && (
        <p className="mt-1 text-sm text-tertiary">
          Complete your profile to unlock unlimited briefs.
        </p>
      )}

      {/* Skills */}
      <section className="mt-8">
        <h2 className="mb-4 font-display text-xl text-primary">Skills</h2>
        <SkillPicker
          selected={profile?.skills || []}
          onChange={handleSkillsChange}
        />
      </section>

      {/* Profile details */}
      <section className="mt-10">
        <h2 className="mb-4 font-display text-xl text-primary">Details</h2>
        <form onSubmit={handleSaveDetails} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-secondary">
              School
            </label>
            <input
              type="text"
              value={school}
              onChange={(e) => setSchool(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-card-border bg-card px-4 py-3 text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="e.g. MIT, Stanford, Stuyvesant High School"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-secondary">
              Graduation year
            </label>
            <input
              type="number"
              value={gradYear}
              onChange={(e) => setGradYear(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-card-border bg-card px-4 py-3 text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="2027"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-secondary">
              Bio
            </label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              className="mt-1 block w-full resize-y rounded-lg border border-card-border bg-card px-4 py-3 text-sm text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="A bit about yourself and what you're looking for..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-secondary">
              GitHub URL
            </label>
            <input
              type="url"
              value={githubUrl}
              onChange={(e) => setGithubUrl(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-card-border bg-card px-4 py-3 text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="https://github.com/yourname"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-secondary">
              Portfolio URL
            </label>
            <input
              type="url"
              value={portfolioUrl}
              onChange={(e) => setPortfolioUrl(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-card-border bg-card px-4 py-3 text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="https://yoursite.com"
            />
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            {saved && (
              <span className="text-sm text-reach-high">Saved</span>
            )}
          </div>
        </form>
      </section>
    </main>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/profile/
git commit -m "feat: add profile page — edit skills and personal details"
```

---

### Task 7: OutreachRow + OutreachForm Components

**Files:**
- Create: `frontend/components/OutreachRow.tsx`
- Create: `frontend/components/OutreachForm.tsx`

- [ ] **Step 1: Create OutreachRow component**

Create `frontend/components/OutreachRow.tsx`:

```tsx
"use client";

import { useState } from "react";
import Link from "next/link";
import { updateOutreach } from "@/lib/api";
import type { OutreachEntry } from "@/lib/types";

const STATUS_OPTIONS = ["sent", "replied", "meeting", "no-response"] as const;

function statusStyle(status: string): string {
  switch (status) {
    case "replied":
      return "bg-reach-high/10 text-reach-high";
    case "meeting":
      return "bg-accent/10 text-accent";
    case "no-response":
      return "bg-reach-med/10 text-reach-med";
    default:
      return "bg-tertiary/10 text-tertiary";
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

interface OutreachRowProps {
  entry: OutreachEntry;
  showCompanyName?: boolean;
  onUpdated?: (updated: OutreachEntry) => void;
}

export default function OutreachRow({
  entry,
  showCompanyName = true,
  onUpdated,
}: OutreachRowProps) {
  const [showDropdown, setShowDropdown] = useState(false);

  const handleStatusChange = async (newStatus: string) => {
    setShowDropdown(false);
    try {
      const updated = await updateOutreach(entry.id, { status: newStatus });
      onUpdated?.(updated);
    } catch {
      // ignore
    }
  };

  return (
    <div className="flex items-center gap-4 rounded-xl border border-card-border bg-card p-4">
      <div className="min-w-0 flex-1">
        {showCompanyName && (
          <Link
            href={`/founder/${entry.company_id}`}
            className="text-sm font-semibold text-primary hover:text-accent"
          >
            {entry.company_name || `Company #${entry.company_id}`}
          </Link>
        )}
        <div className="mt-1 flex items-center gap-3">
          <span className="text-xs text-tertiary">
            {formatDate(entry.sent_at || entry.created_at)}
          </span>
          {entry.notes && (
            <span className="truncate text-xs text-tertiary">
              {entry.notes}
            </span>
          )}
        </div>
      </div>

      {/* Status badge with dropdown */}
      <div className="relative">
        <button
          onClick={() => setShowDropdown(!showDropdown)}
          className={`rounded px-2.5 py-1 text-xs font-semibold ${statusStyle(entry.status)}`}
        >
          {entry.status}
        </button>
        {showDropdown && (
          <div className="absolute right-0 top-8 z-10 rounded-lg border border-card-border bg-card py-1 shadow-card-hover">
            {STATUS_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => handleStatusChange(s)}
                className="block w-full px-4 py-1.5 text-left text-xs text-secondary hover:bg-background hover:text-primary"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create OutreachForm component**

Create `frontend/components/OutreachForm.tsx`:

```tsx
"use client";

import { useState } from "react";
import { createOutreach } from "@/lib/api";
import type { OutreachEntry } from "@/lib/types";

interface OutreachFormProps {
  companyId: number;
  onCreated: (entry: OutreachEntry) => void;
}

export default function OutreachForm({
  companyId,
  onCreated,
}: OutreachFormProps) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState("sent");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const entry = await createOutreach({
        company_id: companyId,
        status,
        notes: notes || null,
        sent_at: new Date().toISOString(),
      });
      onCreated(entry);
      setOpen(false);
      setStatus("sent");
      setNotes("");
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90"
      >
        Log this outreach
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-xl border border-card-border bg-card p-4"
    >
      <div>
        <label className="block text-sm font-medium text-secondary">
          Status
        </label>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="mt-1 block w-full rounded-lg border border-card-border bg-background px-3 py-2 text-sm text-primary focus:border-accent focus:outline-none"
        >
          <option value="sent">Sent</option>
          <option value="replied">Replied</option>
          <option value="meeting">Meeting</option>
          <option value="no-response">No Response</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-secondary">
          Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={2}
          className="mt-1 block w-full resize-y rounded-lg border border-card-border bg-background px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:border-accent focus:outline-none"
          placeholder="Any notes..."
        />
      </div>

      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-lg px-4 py-2 text-sm text-secondary hover:text-primary"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/OutreachRow.tsx frontend/components/OutreachForm.tsx
git commit -m "feat: add OutreachRow and OutreachForm components"
```

---

### Task 8: StatsHeader Component + Tracker Page

**Files:**
- Create: `frontend/components/StatsHeader.tsx`
- Create: `frontend/app/tracker/page.tsx`

- [ ] **Step 1: Create StatsHeader component**

Create `frontend/components/StatsHeader.tsx`:

```tsx
import type { OutreachEntry } from "@/lib/types";

interface StatsHeaderProps {
  entries: OutreachEntry[];
}

export default function StatsHeader({ entries }: StatsHeaderProps) {
  const sent = entries.filter((e) => e.status === "sent").length;
  const replied = entries.filter((e) => e.status === "replied").length;
  const meetings = entries.filter((e) => e.status === "meeting").length;

  const now = new Date();
  const followUps = entries.filter(
    (e) =>
      e.status === "sent" &&
      e.followup_date &&
      new Date(e.followup_date) < now,
  ).length;

  return (
    <div className="space-y-4">
      {/* Follow-up banner */}
      {followUps > 0 && (
        <div className="rounded-xl border-l-4 border-guidance-border bg-guidance-bg px-5 py-3">
          <p className="text-sm font-medium text-primary">
            You have {followUps} follow-up{followUps !== 1 ? "s" : ""} due
          </p>
        </div>
      )}

      {/* Stats boxes */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-2xl font-bold text-primary">{sent}</p>
          <p className="text-xs text-secondary">Sent</p>
        </div>
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-2xl font-bold text-reach-high">{replied}</p>
          <p className="text-xs text-secondary">Replied</p>
        </div>
        <div className="rounded-xl border border-card-border bg-card p-4 text-center">
          <p className="text-2xl font-bold text-accent">{meetings}</p>
          <p className="text-xs text-secondary">Meetings</p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create tracker page**

Create `frontend/app/tracker/page.tsx`:

```tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchOutreach } from "@/lib/api";
import type { OutreachEntry } from "@/lib/types";
import StatsHeader from "@/components/StatsHeader";
import OutreachRow from "@/components/OutreachRow";

const FILTER_OPTIONS = ["all", "sent", "replied", "meeting", "no-response"];

export default function TrackerPage() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const [entries, setEntries] = useState<OutreachEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    if (!authenticated) return;
    fetchOutreach()
      .then((data) => {
        setEntries(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [authenticated]);

  const handleUpdated = useCallback(
    (updated: OutreachEntry) => {
      setEntries((prev) =>
        prev.map((e) => (e.id === updated.id ? { ...e, ...updated } : e)),
      );
    },
    [],
  );

  const filtered =
    filter === "all"
      ? entries
      : entries.filter((e) => e.status === filter);

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="font-display text-3xl text-primary">Outreach Tracker</h1>

      <div className="mt-6">
        <StatsHeader entries={entries} />
      </div>

      {/* Filter chips */}
      <div className="mt-6 flex gap-1.5">
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt}
            onClick={() => setFilter(opt)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              filter === opt
                ? "bg-accent text-white"
                : "border border-card-border bg-card text-secondary hover:text-primary"
            }`}
          >
            {opt.charAt(0).toUpperCase() + opt.slice(1)}
          </button>
        ))}
      </div>

      {/* Outreach list */}
      <div className="mt-4 space-y-3">
        {filtered.length === 0 ? (
          <div className="py-16 text-center">
            <p className="text-secondary">
              No outreach logged yet.{" "}
              <Link href="/feed" className="text-accent hover:underline">
                Visit a founder&apos;s brief
              </Link>{" "}
              to send your first email.
            </p>
          </div>
        ) : (
          filtered.map((entry) => (
            <OutreachRow
              key={entry.id}
              entry={entry}
              onUpdated={handleUpdated}
            />
          ))
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/StatsHeader.tsx frontend/app/tracker/
git commit -m "feat: add tracker page — stats header, filter chips, outreach list"
```

---

### Task 9: Add Outreach Section to Brief Page

**Files:**
- Modify: `frontend/app/founder/[id]/page.tsx`

- [ ] **Step 1: Update brief page with outreach section**

Read `frontend/app/founder/[id]/page.tsx` first. Add imports at the top:

```typescript
import { fetchBrief, fetchOutreach, ApiError } from "@/lib/api";
import type { CompanyBrief, OutreachEntry } from "@/lib/types";
import OutreachForm from "@/components/OutreachForm";
import OutreachRow from "@/components/OutreachRow";
```

(Replace the existing `fetchBrief` and `ApiError` import, and the existing `CompanyBrief` import.)

Add outreach state alongside the existing state declarations:

```typescript
  const [outreach, setOutreach] = useState<OutreachEntry[]>([]);
```

Add outreach fetch inside the existing `useEffect`, after the brief loads successfully. Replace the entire `useEffect` body:

```typescript
  useEffect(() => {
    if (!authenticated) return;

    async function load() {
      try {
        const data = await fetchBrief(Number(id));
        setBrief(data);

        // Fetch outreach for this company
        const allOutreach = await fetchOutreach();
        setOutreach(
          allOutreach.filter((e) => e.company_id === Number(id)),
        );
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError("paywall");
        } else if (err instanceof ApiError && err.status === 404) {
          setError("not-found");
        } else {
          setError("unknown");
        }
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [authenticated, id]);
```

Add handler functions before the return statement:

```typescript
  const handleOutreachCreated = (entry: OutreachEntry) => {
    setOutreach((prev) => [entry, ...prev]);
  };

  const handleOutreachUpdated = (updated: OutreachEntry) => {
    setOutreach((prev) =>
      prev.map((e) => (e.id === updated.id ? { ...e, ...updated } : e)),
    );
  };
```

Finally, in the return JSX, add the outreach section after the `<EmailWorkspace>` component:

```tsx
      <EmailWorkspace
        founderEmail={null}
        companyName={brief.name}
      />

      {/* Outreach section */}
      <div className="mt-8 space-y-4">
        <h3 className="font-display text-lg text-primary">Outreach</h3>
        <OutreachForm
          companyId={brief.id}
          onCreated={handleOutreachCreated}
        />
        {outreach.length > 0 && (
          <div className="space-y-2">
            {outreach.map((entry) => (
              <OutreachRow
                key={entry.id}
                entry={entry}
                showCompanyName={false}
                onUpdated={handleOutreachUpdated}
              />
            ))}
          </div>
        )}
      </div>
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/founder/[id]/page.tsx"
git commit -m "feat: add outreach logging and history to brief page"
```

---

### Task 10: Final Verification

**Files:** None new (verification only)

- [ ] **Step 1: Run full build**

```bash
cd frontend && npm run build
```

Expected: no errors, no warnings. All routes present:
- `/` (landing)
- `/login`, `/signup`
- `/feed`
- `/founder/[id]`
- `/onboard`
- `/profile`
- `/tracker`

- [ ] **Step 2: Verify routes in build output**

Check that the build output lists all expected routes.

- [ ] **Step 3: Commit any remaining changes**

If any fixes were needed, commit them.

```bash
git add -A frontend/
git commit -m "fix: final build fixes for frontend round 2"
```
