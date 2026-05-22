# Frontend Round 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the REACH frontend — landing page with live search + floating founder cards, authenticated feed with wide founder cards, and brief page with guidance card + email workspace.

**Architecture:** Next.js App Router with client-side data fetching from the FastAPI backend. Supabase Auth JS for email+password authentication. All authenticated pages fetch data client-side with loading states. Light theme, distinctive typography (Instrument Serif headlines, DM Sans body).

**Tech Stack:** Next.js 14+, Tailwind CSS, Supabase JS (`@supabase/supabase-js`), TypeScript

**Spec:** `docs/superpowers/specs/2026-05-21-frontend-round1-design.md`

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Create | `frontend/package.json` | Dependencies and scripts |
| Create | `frontend/tsconfig.json` | TypeScript config |
| Create | `frontend/tailwind.config.ts` | Tailwind theme + custom colors |
| Create | `frontend/next.config.ts` | Next.js config |
| Create | `frontend/postcss.config.mjs` | PostCSS for Tailwind |
| Create | `frontend/app/layout.tsx` | Root layout, fonts, Navbar |
| Create | `frontend/app/globals.css` | Tailwind directives + custom styles |
| Create | `frontend/app/page.tsx` | Landing page |
| Create | `frontend/app/login/page.tsx` | Login page |
| Create | `frontend/app/signup/page.tsx` | Signup page |
| Create | `frontend/app/feed/page.tsx` | Feed page |
| Create | `frontend/app/founder/[id]/page.tsx` | Brief page |
| Create | `frontend/lib/supabase.ts` | Supabase client singleton |
| Create | `frontend/lib/api.ts` | API fetch wrapper with auth |
| Create | `frontend/lib/types.ts` | TypeScript types matching backend schemas |
| Create | `frontend/lib/useAuth.ts` | Auth hook — session state + redirect helpers |
| Create | `frontend/components/Navbar.tsx` | Logo + nav + auth state |
| Create | `frontend/components/AuthForm.tsx` | Shared email+password form |
| Create | `frontend/components/SearchBar.tsx` | Large search input with debounce |
| Create | `frontend/components/FounderCard.tsx` | Wide horizontal founder card |
| Create | `frontend/components/FloatingCards.tsx` | Animated floating cards for landing |
| Create | `frontend/components/FilterBar.tsx` | Industry dropdown + reachability chips |
| Create | `frontend/components/LoadMoreButton.tsx` | "Show more" pagination button |
| Create | `frontend/components/FounderBrief.tsx` | Full enriched data display |
| Create | `frontend/components/GuidanceCard.tsx` | Visually distinct guidance panel |
| Create | `frontend/components/EmailWorkspace.tsx` | Textarea + word count + Gmail button |

---

### Task 1: Scaffold Next.js Project

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/next.config.ts`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/page.tsx`
- Create: `frontend/.env.local`

- [ ] **Step 1: Create the Next.js project**

Run from the repo root:

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

Accept defaults. This generates the scaffold.

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install @supabase/supabase-js
```

- [ ] **Step 3: Create environment file**

Create `frontend/.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 4: Configure Tailwind with custom theme**

Replace `frontend/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#fafafa",
        card: "#ffffff",
        "card-border": "#e5e5e5",
        primary: "#1a1a1a",
        secondary: "#666666",
        tertiary: "#999999",
        accent: "#0d9488",
        "reach-high": "#16a34a",
        "reach-med": "#d97706",
        "reach-low": "#9ca3af",
        "guidance-bg": "#f0fdfa",
        "guidance-border": "#0d9488",
      },
      fontFamily: {
        display: ["var(--font-instrument-serif)", "Georgia", "serif"],
        body: ["var(--font-dm-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,0.08)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.12)",
        float: "0 8px 24px rgba(0,0,0,0.1)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: Set up root layout with fonts**

Replace `frontend/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { Instrument_Serif, DM_Sans } from "next/font/google";
import "./globals.css";

const instrumentSerif = Instrument_Serif({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-instrument-serif",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "REACH — Cold email the founders who actually respond",
  description:
    "A curated directory of reachable YC founders for ambitious students.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${instrumentSerif.variable} ${dmSans.variable}`}
    >
      <body className="bg-background font-body text-primary antialiased">
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 6: Set up globals.css**

Replace `frontend/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 7: Create a minimal landing page placeholder**

Replace `frontend/app/page.tsx`:

```tsx
export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      <h1 className="font-display text-5xl text-primary">REACH</h1>
      <p className="mt-4 text-secondary">Coming soon</p>
    </main>
  );
}
```

- [ ] **Step 8: Verify the dev server starts**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`. Expected: see "REACH" in serif font on off-white background.

- [ ] **Step 9: Verify the build succeeds**

```bash
cd frontend && npm run build
```

Expected: build completes with no errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Next.js frontend with Tailwind + custom theme"
```

---

### Task 2: TypeScript Types + API Client + Auth Utilities

**Files:**
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/supabase.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/useAuth.ts`

- [ ] **Step 1: Create TypeScript types matching backend schemas**

Create `frontend/lib/types.ts`:

```typescript
export interface CompanyCard {
  id: number;
  name: string;
  yc_batch: string | null;
  one_liner: string | null;
  industry: string | null;
  stage_detail: string | null;
  technical_level: string | null;
  team_size: number | null;
  reachability_score: string | null;
  need_tags: string[];
  match_score: number;
  rank_score: number;
}

export interface Guidance {
  your_angle: string;
  reference_this: string;
  dont_say: string;
  your_ask: string;
}

export interface CompanyBrief {
  id: number;
  name: string;
  yc_batch: string | null;
  description: string | null;
  summary: string | null;
  one_liner: string | null;
  website: string | null;
  industry: string | null;
  stage: string | null;
  stage_detail: string | null;
  technical_level: string | null;
  team_size: number | null;
  need_tags: string[];
  specific_projects: string[];
  reachability_score: string | null;
  reachability_probability: number | null;
  founder_name: string | null;
  founder_title: string | null;
  founder_linkedin: string | null;
  founder_twitter: string | null;
  all_locations: string | null;
  tags: string[];
  industries: string[];
  match_score: number;
  guidance: Guidance | null;
}

export interface UserProfile {
  id: string;
  email: string;
  school: string | null;
  grad_year: number | null;
  skills: string[];
  bio: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  tier: string;
}

export const INDUSTRIES = [
  "fintech", "healthcare", "biotech", "developer-tools", "ai-ml",
  "education", "e-commerce", "logistics", "real-estate", "legal",
  "security", "enterprise-saas", "consumer", "media", "hardware",
  "climate", "aerospace", "gaming", "food-beverage", "manufacturing",
  "travel", "hr-recruiting", "insurance", "construction", "agriculture",
  "transportation", "government", "social-impact", "energy", "other",
] as const;
```

- [ ] **Step 2: Create Supabase client**

Create `frontend/lib/supabase.ts`:

```typescript
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

- [ ] **Step 3: Create API fetch wrapper**

Create `frontend/lib/api.ts`:

```typescript
import { supabase } from "./supabase";
import type { CompanyCard, CompanyBrief } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function authHeaders(): Promise<Record<string, string>> {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token) {
    return { Authorization: `Bearer ${session.access_token}` };
  }
  return {};
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = await authHeaders();
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail || "Request failed");
  }

  return res.json();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function fetchCompanies(params?: {
  industry?: string;
  reachability?: string;
  page?: number;
  limit?: number;
}): Promise<CompanyCard[]> {
  const query = new URLSearchParams();
  if (params?.industry) query.set("industry", params.industry);
  if (params?.reachability) query.set("reachability", params.reachability);
  if (params?.page) query.set("page", String(params.page));
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return apiFetch<CompanyCard[]>(`/companies${qs ? `?${qs}` : ""}`);
}

export async function fetchBrief(id: number): Promise<CompanyBrief> {
  return apiFetch<CompanyBrief>(`/companies/${id}`);
}
```

- [ ] **Step 4: Create auth hook**

Create `frontend/lib/useAuth.ts`:

```typescript
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "./supabase";

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  return { session, loading, user: session?.user ?? null };
}

export function useRequireAuth() {
  const { session, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !session) {
      router.replace("/login");
    }
  }, [session, loading, router]);

  return { session, loading, authenticated: !!session };
}
```

- [ ] **Step 5: Verify build succeeds**

```bash
cd frontend && npm run build
```

Expected: no type errors, build passes.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/
git commit -m "feat: add TypeScript types, Supabase client, API wrapper, auth hook"
```

---

### Task 3: AuthForm + Login + Signup Pages

**Files:**
- Create: `frontend/components/AuthForm.tsx`
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/signup/page.tsx`

- [ ] **Step 1: Create AuthForm component**

Create `frontend/components/AuthForm.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";

interface AuthFormProps {
  mode: "login" | "signup";
}

export default function AuthForm({ mode }: AuthFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
      }

      const q = searchParams.get("q");
      router.push(q ? `/feed?q=${encodeURIComponent(q)}` : "/feed");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Something went wrong";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-secondary"
        >
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mt-1 block w-full rounded-lg border border-card-border bg-card px-4 py-3 text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          placeholder="you@school.edu"
        />
      </div>

      <div>
        <label
          htmlFor="password"
          className="block text-sm font-medium text-secondary"
        >
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
          className="mt-1 block w-full rounded-lg border border-card-border bg-card px-4 py-3 text-primary placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
          placeholder="••••••••"
        />
      </div>

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-accent px-4 py-3 font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-50"
      >
        {loading
          ? "..."
          : mode === "signup"
            ? "Create account"
            : "Sign in"}
      </button>

      <p className="text-center text-sm text-secondary">
        {mode === "signup" ? (
          <>
            Already have an account?{" "}
            <Link href="/login" className="text-accent hover:underline">
              Sign in
            </Link>
          </>
        ) : (
          <>
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-accent hover:underline">
              Sign up
            </Link>
          </>
        )}
      </p>
    </form>
  );
}
```

- [ ] **Step 2: Create login page**

Create `frontend/app/login/page.tsx`:

```tsx
import { Suspense } from "react";
import AuthForm from "@/components/AuthForm";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <h1 className="mb-2 font-display text-3xl">Welcome back</h1>
      <p className="mb-8 text-secondary">Sign in to continue</p>
      <Suspense>
        <AuthForm mode="login" />
      </Suspense>
    </main>
  );
}
```

- [ ] **Step 3: Create signup page**

Create `frontend/app/signup/page.tsx`:

```tsx
import { Suspense } from "react";
import AuthForm from "@/components/AuthForm";

export default function SignupPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <h1 className="mb-2 font-display text-3xl">Get started</h1>
      <p className="mb-8 text-secondary">
        Find the founders who actually respond
      </p>
      <Suspense>
        <AuthForm mode="signup" />
      </Suspense>
    </main>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 5: Verify visually**

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000/login` and `http://localhost:3000/signup`. Expected: centered forms with email/password inputs, styled with the custom theme.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/AuthForm.tsx frontend/app/login/ frontend/app/signup/
git commit -m "feat: add AuthForm component + login and signup pages"
```

---

### Task 4: Navbar Component

**Files:**
- Create: `frontend/components/Navbar.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Create Navbar component**

Create `frontend/components/Navbar.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { supabase } from "@/lib/supabase";

export default function Navbar() {
  const { session, loading } = useAuth();
  const router = useRouter();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/");
  };

  return (
    <nav className="fixed top-0 z-50 w-full border-b border-card-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
        <Link href={session ? "/feed" : "/"} className="font-display text-xl">
          REACH
        </Link>

        {!loading && (
          <div className="flex items-center gap-4">
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
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-sm text-secondary hover:text-primary"
                >
                  Sign in
                </Link>
                <Link
                  href="/signup"
                  className="rounded-lg bg-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-accent/90"
                >
                  Sign up
                </Link>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Add Navbar to root layout**

In `frontend/app/layout.tsx`, add the import and render Navbar inside `<body>`:

```tsx
import type { Metadata } from "next";
import { Instrument_Serif, DM_Sans } from "next/font/google";
import Navbar from "@/components/Navbar";
import "./globals.css";

const instrumentSerif = Instrument_Serif({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-instrument-serif",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "REACH — Cold email the founders who actually respond",
  description:
    "A curated directory of reachable YC founders for ambitious students.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${instrumentSerif.variable} ${dmSans.variable}`}
    >
      <body className="bg-background font-body text-primary antialiased">
        <Navbar />
        <div className="pt-14">{children}</div>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Verify build and visual**

```bash
cd frontend && npm run build
```

Then `npm run dev` — check that the navbar appears fixed at top on all pages.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/Navbar.tsx frontend/app/layout.tsx
git commit -m "feat: add Navbar with auth state and fixed positioning"
```

---

### Task 5: FounderCard Component

**Files:**
- Create: `frontend/components/FounderCard.tsx`

- [ ] **Step 1: Create FounderCard component**

Create `frontend/components/FounderCard.tsx`:

```tsx
"use client";

import Link from "next/link";
import type { CompanyCard } from "@/lib/types";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function reachabilityColor(score: string | null): string {
  switch (score) {
    case "high":
      return "bg-reach-high/10 text-reach-high";
    case "medium":
      return "bg-reach-med/10 text-reach-med";
    default:
      return "bg-reach-low/10 text-reach-low";
  }
}

interface FounderCardProps {
  company: CompanyCard;
  onClick?: () => void;
}

export default function FounderCard({ company, onClick }: FounderCardProps) {
  const displayName = company.name;
  const initials = getInitials(displayName);

  const content = (
    <div className="flex items-center gap-5 rounded-xl border border-card-border bg-card p-5 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover">
      <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-accent/10 font-display text-lg text-accent">
        {initials}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <h3 className="truncate text-base font-semibold text-primary">
            {displayName}
          </h3>
          {company.reachability_score && (
            <span
              className={`flex-shrink-0 rounded px-2 py-0.5 text-xs font-semibold uppercase ${reachabilityColor(company.reachability_score)}`}
            >
              {company.reachability_score}
            </span>
          )}
        </div>

        <p className="mt-0.5 text-sm text-secondary">
          Founder · {company.name}
          {company.yc_batch ? ` · ${company.yc_batch}` : ""}
        </p>

        {company.one_liner && (
          <p className="mt-1.5 truncate text-sm text-tertiary">
            {company.one_liner}
          </p>
        )}

        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {company.industry && (
            <span className="rounded bg-background px-2 py-0.5 text-xs text-secondary">
              {company.industry}
            </span>
          )}
          {company.team_size && (
            <span className="rounded bg-background px-2 py-0.5 text-xs text-secondary">
              {company.team_size} people
            </span>
          )}
          {company.match_score > 0 && (
            <span className="rounded bg-accent/10 px-2 py-0.5 text-xs text-accent">
              {company.match_score} skill{company.match_score !== 1 ? "s" : ""}{" "}
              match
            </span>
          )}
        </div>
      </div>
    </div>
  );

  if (onClick) {
    return (
      <button onClick={onClick} className="block w-full text-left">
        {content}
      </button>
    );
  }

  return (
    <Link href={`/founder/${company.id}`} className="block">
      {content}
    </Link>
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
git add frontend/components/FounderCard.tsx
git commit -m "feat: add FounderCard — wide horizontal card with avatar + metadata"
```

---

### Task 6: SearchBar Component

**Files:**
- Create: `frontend/components/SearchBar.tsx`

- [ ] **Step 1: Create SearchBar component**

Create `frontend/components/SearchBar.tsx`:

```tsx
"use client";

import { useState, useEffect, useRef } from "react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  onSubmit?: (query: string) => void;
  placeholder?: string;
  debounceMs?: number;
  initialValue?: string;
}

export default function SearchBar({
  onSearch,
  onSubmit,
  placeholder = "Cold email the founders who actually respond",
  debounceMs = 300,
  initialValue = "",
}: SearchBarProps) {
  const [value, setValue] = useState(initialValue);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

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
    <div className="w-full max-w-2xl">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full rounded-xl border border-card-border bg-card px-6 py-4 text-lg text-primary shadow-card placeholder:text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
      />
    </div>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/SearchBar.tsx
git commit -m "feat: add SearchBar with debounced search and Enter handling"
```

---

### Task 7: FilterBar + LoadMoreButton

**Files:**
- Create: `frontend/components/FilterBar.tsx`
- Create: `frontend/components/LoadMoreButton.tsx`

- [ ] **Step 1: Create FilterBar component**

Create `frontend/components/FilterBar.tsx`:

```tsx
"use client";

import { INDUSTRIES } from "@/lib/types";

interface FilterBarProps {
  industry: string;
  reachability: string;
  onIndustryChange: (value: string) => void;
  onReachabilityChange: (value: string) => void;
}

const REACHABILITY_OPTIONS = ["all", "high", "medium", "low"];

export default function FilterBar({
  industry,
  reachability,
  onIndustryChange,
  onReachabilityChange,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={industry}
        onChange={(e) => onIndustryChange(e.target.value)}
        className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary focus:border-accent focus:outline-none"
      >
        <option value="">All industries</option>
        {INDUSTRIES.map((ind) => (
          <option key={ind} value={ind}>
            {ind.replace(/-/g, " ")}
          </option>
        ))}
      </select>

      <div className="flex gap-1.5">
        {REACHABILITY_OPTIONS.map((level) => (
          <button
            key={level}
            onClick={() =>
              onReachabilityChange(level === "all" ? "" : level)
            }
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              (level === "all" && reachability === "") ||
              level === reachability
                ? "bg-accent text-white"
                : "bg-card text-secondary border border-card-border hover:text-primary"
            }`}
          >
            {level.charAt(0).toUpperCase() + level.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create LoadMoreButton component**

Create `frontend/components/LoadMoreButton.tsx`:

```tsx
"use client";

interface LoadMoreButtonProps {
  onClick: () => void;
  loading: boolean;
  hasMore: boolean;
}

export default function LoadMoreButton({
  onClick,
  loading,
  hasMore,
}: LoadMoreButtonProps) {
  if (!hasMore) return null;

  return (
    <div className="flex justify-center py-8">
      <button
        onClick={onClick}
        disabled={loading}
        className="rounded-lg border border-card-border bg-card px-8 py-3 text-sm font-medium text-secondary transition-colors hover:border-accent hover:text-accent disabled:opacity-50"
      >
        {loading ? "Loading..." : "Show more founders"}
      </button>
    </div>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/FilterBar.tsx frontend/components/LoadMoreButton.tsx
git commit -m "feat: add FilterBar and LoadMoreButton for feed pagination"
```

---

### Task 8: Feed Page

**Files:**
- Create: `frontend/app/feed/page.tsx`

- [ ] **Step 1: Create feed page**

Create `frontend/app/feed/page.tsx`:

```tsx
"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchCompanies } from "@/lib/api";
import type { CompanyCard as CompanyCardType } from "@/lib/types";
import SearchBar from "@/components/SearchBar";
import FilterBar from "@/components/FilterBar";
import FounderCard from "@/components/FounderCard";
import LoadMoreButton from "@/components/LoadMoreButton";

const PAGE_SIZE = 20;

function FeedContent() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [companies, setCompanies] = useState<CompanyCardType[]>([]);
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [industry, setIndustry] = useState("");
  const [reachability, setReachability] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadCompanies = useCallback(
    async (pageNum: number, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);

      try {
        const data = await fetchCompanies({
          industry: industry || undefined,
          reachability: reachability || undefined,
          page: pageNum,
          limit: PAGE_SIZE,
        });

        if (append) {
          setCompanies((prev) => [...prev, ...data]);
        } else {
          setCompanies(data);
        }
        setHasMore(data.length === PAGE_SIZE);
      } catch {
        setHasMore(false);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [industry, reachability],
  );

  useEffect(() => {
    if (authenticated) {
      setPage(1);
      loadCompanies(1, false);
    }
  }, [authenticated, industry, reachability, loadCompanies]);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadCompanies(nextPage, true);
  };

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
  }, []);

  // Client-side filter on search query
  const filtered = searchQuery
    ? companies.filter(
        (c) =>
          c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (c.one_liner &&
            c.one_liner.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (c.industry &&
            c.industry.toLowerCase().includes(searchQuery.toLowerCase())),
      )
    : companies;

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-8">
      <div className="mb-6 flex flex-col items-center gap-4">
        <SearchBar
          onSearch={handleSearch}
          placeholder="Search founders..."
          initialValue={initialQuery}
        />
        <FilterBar
          industry={industry}
          reachability={reachability}
          onIndustryChange={setIndustry}
          onReachabilityChange={setReachability}
        />
      </div>

      {loading ? (
        <div className="py-20 text-center text-secondary">
          Loading founders...
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-20 text-center text-secondary">
          No founders match your search. Try different keywords.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((company) => (
            <FounderCard key={company.id} company={company} />
          ))}
        </div>
      )}

      <LoadMoreButton
        onClick={handleLoadMore}
        loading={loadingMore}
        hasMore={hasMore && !searchQuery}
      />
    </main>
  );
}

export default function FeedPage() {
  return (
    <Suspense>
      <FeedContent />
    </Suspense>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Verify visually**

Run `npm run dev`, go to `http://localhost:3000/feed`. Should redirect to `/login` if not authenticated. If you set up Supabase credentials and log in, you should see the search bar, filters, and founder cards loading from the API.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/feed/
git commit -m "feat: add feed page — search, filters, founder cards, load more"
```

---

### Task 9: GuidanceCard + EmailWorkspace

**Files:**
- Create: `frontend/components/GuidanceCard.tsx`
- Create: `frontend/components/EmailWorkspace.tsx`

- [ ] **Step 1: Create GuidanceCard component**

Create `frontend/components/GuidanceCard.tsx`:

```tsx
import type { Guidance } from "@/lib/types";

interface GuidanceCardProps {
  guidance: Guidance | null;
}

function GuidanceField({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <dt className="text-sm font-semibold text-accent">{label}</dt>
      <dd className="mt-1 text-sm leading-relaxed text-primary">{text}</dd>
    </div>
  );
}

export default function GuidanceCard({ guidance }: GuidanceCardProps) {
  if (!guidance) {
    return (
      <div className="rounded-xl border border-card-border bg-card p-6">
        <p className="text-sm text-secondary">
          Add skills to your profile to get personalized guidance.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-l-4 border-guidance-border bg-guidance-bg p-6">
      <h3 className="mb-4 font-display text-lg text-primary">Your Approach</h3>
      <dl className="space-y-4">
        <GuidanceField label="Your angle" text={guidance.your_angle} />
        <GuidanceField label="Reference this" text={guidance.reference_this} />
        <GuidanceField label="Don't say" text={guidance.dont_say} />
        <GuidanceField label="Your ask" text={guidance.your_ask} />
      </dl>
    </div>
  );
}
```

- [ ] **Step 2: Create EmailWorkspace component**

Create `frontend/components/EmailWorkspace.tsx`:

```tsx
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
  const count = wordCount(body);

  const mailtoHref = founderEmail
    ? `mailto:${founderEmail}?subject=${encodeURIComponent(`Quick question — ${companyName}`)}&body=${encodeURIComponent(body)}`
    : undefined;

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

      <div className="flex items-center justify-between">
        <p className={`text-sm ${countColor(count)}`}>
          {count} word{count !== 1 ? "s" : ""}{" "}
          <span className="text-tertiary">· Aim for under 150 words</span>
        </p>

        {founderEmail ? (
          <a
            href={mailtoHref}
            className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90"
          >
            Open in Gmail
          </a>
        ) : (
          <span className="text-sm text-tertiary">
            Email not available yet
          </span>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/GuidanceCard.tsx frontend/components/EmailWorkspace.tsx
git commit -m "feat: add GuidanceCard and EmailWorkspace components"
```

---

### Task 10: FounderBrief + Brief Page

**Files:**
- Create: `frontend/components/FounderBrief.tsx`
- Create: `frontend/app/founder/[id]/page.tsx`

- [ ] **Step 1: Create FounderBrief component**

Create `frontend/components/FounderBrief.tsx`:

```tsx
import type { CompanyBrief } from "@/lib/types";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function reachabilityColor(score: string | null): string {
  switch (score) {
    case "high":
      return "bg-reach-high/10 text-reach-high";
    case "medium":
      return "bg-reach-med/10 text-reach-med";
    default:
      return "bg-reach-low/10 text-reach-low";
  }
}

interface FounderBriefProps {
  brief: CompanyBrief;
}

export default function FounderBrief({ brief }: FounderBriefProps) {
  const displayName = brief.founder_name || brief.name;
  const title = brief.founder_title || "Founder";
  const initials = getInitials(displayName);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start gap-5">
        <div className="flex h-20 w-20 flex-shrink-0 items-center justify-center rounded-full bg-accent/10 font-display text-2xl text-accent">
          {initials}
        </div>
        <div>
          <h1 className="font-display text-3xl text-primary">{displayName}</h1>
          <p className="mt-1 text-lg text-secondary">
            {title} · {brief.name}
          </p>

          <div className="mt-3 flex flex-wrap gap-2">
            {brief.yc_batch && (
              <span className="rounded bg-background px-2.5 py-1 text-xs font-medium text-secondary">
                {brief.yc_batch}
              </span>
            )}
            {brief.industry && (
              <span className="rounded bg-background px-2.5 py-1 text-xs text-secondary">
                {brief.industry.replace(/-/g, " ")}
              </span>
            )}
            {brief.team_size && (
              <span className="rounded bg-background px-2.5 py-1 text-xs text-secondary">
                {brief.team_size} people
              </span>
            )}
            {brief.reachability_score && (
              <span
                className={`rounded px-2.5 py-1 text-xs font-semibold uppercase ${reachabilityColor(brief.reachability_score)}`}
              >
                {brief.reachability_score} reachability
              </span>
            )}
          </div>

          {/* Links */}
          <div className="mt-3 flex gap-3">
            {brief.website && (
              <a
                href={brief.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent hover:underline"
              >
                Website
              </a>
            )}
            {brief.founder_linkedin && (
              <a
                href={brief.founder_linkedin}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent hover:underline"
              >
                LinkedIn
              </a>
            )}
            {brief.founder_twitter && (
              <a
                href={brief.founder_twitter}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-accent hover:underline"
              >
                Twitter
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Company Info */}
      <section className="space-y-4">
        {brief.summary && (
          <p className="leading-relaxed text-primary">{brief.summary}</p>
        )}

        {brief.one_liner && (
          <p className="text-sm italic text-secondary">{brief.one_liner}</p>
        )}

        <div className="flex flex-wrap gap-2">
          {brief.stage_detail && (
            <span className="rounded-lg border border-card-border px-3 py-1 text-xs text-secondary">
              {brief.stage_detail}
            </span>
          )}
          {brief.technical_level && (
            <span className="rounded-lg border border-card-border px-3 py-1 text-xs text-secondary">
              {brief.technical_level}
            </span>
          )}
        </div>

        {/* Need tags */}
        {brief.need_tags.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-secondary">
              Skills they need
            </h3>
            <div className="flex flex-wrap gap-1.5">
              {brief.need_tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-accent/10 px-3 py-1 text-xs text-accent"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Specific projects */}
        {brief.specific_projects.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-secondary">
              What you could help with
            </h3>
            <ul className="space-y-2">
              {brief.specific_projects.map((project, i) => (
                <li
                  key={i}
                  className="rounded-lg bg-background p-3 text-sm leading-relaxed text-primary"
                >
                  {project}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Create brief page**

Create `frontend/app/founder/[id]/page.tsx`:

```tsx
"use client";

import { useState, useEffect, use } from "react";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchBrief, ApiError } from "@/lib/api";
import type { CompanyBrief } from "@/lib/types";
import FounderBrief from "@/components/FounderBrief";
import GuidanceCard from "@/components/GuidanceCard";
import EmailWorkspace from "@/components/EmailWorkspace";

export default function BriefPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { authenticated, loading: authLoading } = useRequireAuth();
  const [brief, setBrief] = useState<CompanyBrief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authenticated) return;

    async function load() {
      try {
        const data = await fetchBrief(Number(id));
        setBrief(data);
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

  if (authLoading || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  if (error === "paywall") {
    return (
      <main className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h2 className="font-display text-2xl text-primary">
          You&apos;ve used your 3 free briefs
        </h2>
        <p className="mt-3 text-secondary">
          Complete your profile to unlock unlimited access.
        </p>
      </main>
    );
  }

  if (error === "not-found") {
    return (
      <main className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h2 className="font-display text-2xl text-primary">
          Founder not found
        </h2>
        <p className="mt-3 text-secondary">
          This page doesn&apos;t exist or has been removed.
        </p>
      </main>
    );
  }

  if (error || !brief) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-20 text-center">
        <h2 className="font-display text-2xl text-primary">
          Something went wrong
        </h2>
        <p className="mt-3 text-secondary">Please try again later.</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-8">
      <FounderBrief brief={brief} />

      <div className="my-8">
        <GuidanceCard guidance={brief.guidance} />
      </div>

      <EmailWorkspace
        founderEmail={null}
        companyName={brief.name}
      />
    </main>
  );
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 4: Verify visually**

Run `npm run dev`. Navigate to `/founder/1` (if authenticated). Should show the full brief with header, company info, guidance card, and email workspace.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/FounderBrief.tsx frontend/app/founder/
git commit -m "feat: add FounderBrief component and brief page with guidance + email"
```

---

### Task 11: FloatingCards + Landing Page

**Files:**
- Create: `frontend/components/FloatingCards.tsx`
- Modify: `frontend/app/page.tsx`

- [ ] **Step 1: Create FloatingCards component**

Create `frontend/components/FloatingCards.tsx`:

```tsx
"use client";

import type { CompanyCard } from "@/lib/types";

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function reachabilityColor(score: string | null): string {
  switch (score) {
    case "high":
      return "bg-reach-high/10 text-reach-high";
    case "medium":
      return "bg-reach-med/10 text-reach-med";
    default:
      return "bg-reach-low/10 text-reach-low";
  }
}

const POSITIONS = [
  { top: "8%", left: "5%", rotate: "-3deg", delay: "0s" },
  { top: "12%", right: "8%", rotate: "2.5deg", delay: "0.5s" },
  { top: "40%", left: "3%", rotate: "1.5deg", delay: "1s" },
  { top: "45%", right: "4%", rotate: "-2deg", delay: "0.3s" },
  { top: "70%", left: "8%", rotate: "2deg", delay: "0.8s" },
  { top: "68%", right: "6%", rotate: "-1.5deg", delay: "0.6s" },
];

interface FloatingCardsProps {
  companies: CompanyCard[];
  onCardClick?: (company: CompanyCard) => void;
}

export default function FloatingCards({
  companies,
  onCardClick,
}: FloatingCardsProps) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {companies.slice(0, 6).map((company, i) => {
        const pos = POSITIONS[i % POSITIONS.length];
        return (
          <div
            key={company.id}
            className="pointer-events-auto absolute animate-float cursor-pointer opacity-60 transition-opacity duration-300 hover:opacity-90"
            style={{
              top: pos.top,
              left: pos.left,
              right: pos.right,
              transform: `rotate(${pos.rotate})`,
              animationDelay: pos.delay,
            }}
            onClick={() => onCardClick?.(company)}
          >
            <div className="flex items-center gap-3 rounded-xl border border-card-border bg-card/90 p-4 shadow-float backdrop-blur-sm">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-accent/10 text-sm font-semibold text-accent">
                {getInitials(company.name)}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-primary">
                  {company.name}
                </p>
                <p className="text-xs text-secondary">
                  Founder
                  {company.yc_batch ? ` · ${company.yc_batch}` : ""}
                </p>
                {company.one_liner && (
                  <p className="mt-0.5 max-w-[200px] truncate text-xs text-tertiary">
                    {company.one_liner}
                  </p>
                )}
              </div>
              {company.reachability_score && (
                <span
                  className={`ml-2 flex-shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${reachabilityColor(company.reachability_score)}`}
                >
                  {company.reachability_score}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 2: Add float animation to globals.css**

Append to `frontend/app/globals.css`:

```css
@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(var(--tw-rotate, 0deg)); }
  50% { transform: translateY(-12px) rotate(var(--tw-rotate, 0deg)); }
}

.animate-float {
  animation: float 6s ease-in-out infinite;
}
```

- [ ] **Step 3: Build the landing page**

Replace `frontend/app/page.tsx`:

```tsx
"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/useAuth";
import { fetchCompanies } from "@/lib/api";
import type { CompanyCard } from "@/lib/types";
import SearchBar from "@/components/SearchBar";
import FloatingCards from "@/components/FloatingCards";

export default function LandingPage() {
  const { session, loading: authLoading } = useAuth();
  const router = useRouter();
  const [companies, setCompanies] = useState<CompanyCard[]>([]);

  // Redirect logged-in users to feed
  useEffect(() => {
    if (!authLoading && session) {
      router.replace("/feed");
    }
  }, [session, authLoading, router]);

  // Load initial floating cards
  useEffect(() => {
    fetchCompanies({ limit: 6 })
      .then(setCompanies)
      .catch(() => {});
  }, []);

  const handleSearch = useCallback((query: string) => {
    if (!query.trim()) {
      fetchCompanies({ limit: 6 })
        .then(setCompanies)
        .catch(() => {});
      return;
    }
    // Fetch a larger set and filter client-side
    fetchCompanies({ limit: 50 }).then((data) => {
      const q = query.toLowerCase();
      const filtered = data.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          (c.one_liner && c.one_liner.toLowerCase().includes(q)) ||
          (c.industry && c.industry.toLowerCase().includes(q)),
      );
      setCompanies(filtered.slice(0, 6));
    }).catch(() => {});
  }, []);

  const handleSubmit = (query: string) => {
    router.push(`/login?q=${encodeURIComponent(query)}`);
  };

  const handleCardClick = () => {
    router.push("/login");
  };

  if (authLoading) return null;

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6">
      <FloatingCards companies={companies} onCardClick={handleCardClick} />

      <div className="relative z-10 flex flex-col items-center text-center">
        <h1 className="max-w-xl font-display text-5xl leading-tight text-primary md:text-6xl">
          You don&apos;t need connections. You need the right founder.
        </h1>

        <div className="mt-10 w-full max-w-2xl">
          <SearchBar
            onSearch={handleSearch}
            onSubmit={handleSubmit}
          />
        </div>
      </div>

      <div className="relative z-10 mt-32 flex flex-col items-center gap-4 pb-16">
        <p className="text-secondary">
          A curated directory of 750+ reachable YC founders
        </p>
        <a
          href="/signup"
          className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent/90"
        >
          Sign up free
        </a>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 5: Verify visually**

Run `npm run dev`. Go to `http://localhost:3000`. Expected: centered headline with serif font, search bar below, floating cards scattered behind with subtle drift animation.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/FloatingCards.tsx frontend/app/globals.css frontend/app/page.tsx
git commit -m "feat: add landing page with hero, live search, and floating founder cards"
```

---

### Task 12: Final Verification + Polish

**Files:** None new (verification + minor fixes only)

- [ ] **Step 1: Run full build**

```bash
cd frontend && npm run build
```

Expected: no errors, no warnings.

- [ ] **Step 2: Test full flow visually**

Run `npm run dev` and manually check:

1. `/` — Landing page loads with headline, search bar, floating cards
2. Type in search bar — cards change
3. Press Enter — redirects to `/login?q=...`
4. `/login` — form renders, link to signup works
5. `/signup` — form renders, link to login works
6. `/feed` — redirects to `/login` if not authenticated
7. `/founder/1` — redirects to `/login` if not authenticated

If Supabase is configured, also test:
8. Sign up → redirects to `/feed`
9. Feed shows founder cards from API
10. Click card → brief page loads with all sections
11. Guidance card shows if user has skills
12. Email workspace word count works
13. Navbar shows "Sign out" when logged in
14. Sign out → back to landing page

- [ ] **Step 3: Commit any fixes**

If any issues found during verification, fix and commit:

```bash
git add frontend/
git commit -m "fix: polish from final verification"
```
