"use client";

import { useState, useEffect, useRef } from "react";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchProfile, updateProfile, getGmailStatus, getGmailAuthUrl, disconnectGmail, fetchRepos, createRepo, deleteRepo, uploadResume, deleteResume } from "@/lib/api";
import type { GmailStatus } from "@/lib/types";
import type { UserProfile } from "@/lib/types";
import type { UserRepo } from "@/lib/types";
import InterestPicker from "@/components/InterestPicker";

const TECH_TERMS = new Set([
  "python", "javascript", "typescript", "react", "next", "nextjs", "node",
  "java", "kotlin", "swift", "rust", "go", "golang", "c++", "c#",
  "ruby", "php", "sql", "html", "css", "tailwind",
  "api", "rest", "graphql", "websocket",
  "ml", "ai", "machine learning", "deep learning", "nlp", "llm",
  "pytorch", "tensorflow", "scikit",
  "docker", "kubernetes", "aws", "gcp", "azure", "vercel", "supabase",
  "firebase", "postgres", "mongodb", "redis", "sqlite",
  "git", "github", "linux", "vim",
  "figma", "sketch", "design",
  "flutter", "react native", "ios", "android",
  "scraper", "bot", "cli", "dashboard", "app", "web",
  "data", "analytics", "pipeline", "etl",
  "blockchain", "crypto", "web3", "solidity",
  "opencv", "selenium", "playwright", "puppeteer",
  "arduino", "raspberry pi", "iot",
]);

function hasSpecificTerm(text: string): boolean {
  const lower = text.toLowerCase();
  for (const term of TECH_TERMS) {
    if (lower.includes(term)) return true;
  }
  return false;
}

function bioWordCount(text: string): number {
  return text.trim() === "" ? 0 : text.trim().split(/\s+/).length;
}

export default function ProfilePage() {
  const { authenticated, loading: authLoading } = useRequireAuth();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  // Form fields
  const [school, setSchool] = useState("");
  const [gradYear, setGradYear] = useState("");
  const [bioGrade, setBioGrade] = useState("");
  const [bioBuilding, setBioBuilding] = useState("");
  const [bioInterests, setBioInterests] = useState("");
  const [bioLegacy, setBioLegacy] = useState<string | null>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [interests, setInterests] = useState<string[]>([]);
  const [resumeUrl, setResumeUrl] = useState("");
  const [repos, setRepos] = useState<UserRepo[]>([]);
  const [repoUrl, setRepoUrl] = useState("");
  const [repoLoading, setRepoLoading] = useState(false);
  const [repoError, setRepoError] = useState<string | null>(null);
  const [location, setLocation] = useState("");
  const [resumeFile, setResumeFile] = useState<string | null>(null);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [gmail, setGmail] = useState<GmailStatus>({ connected: false, gmail_email: null });
  const [gmailLoading, setGmailLoading] = useState(false);

  const savedTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (!authenticated) return;

    fetchProfile()
      .then((p) => {
        setProfile(p);
        setSchool(p.school ?? "");
        setGradYear(p.grad_year != null ? String(p.grad_year) : "");
        const bioStr = p.bio ?? "";
        const structuredMatch = bioStr.match(
          /^I'm a (.+?)\.\s+(.+?)\.\s+I'm interested in (.+)\.?$/
        );
        if (structuredMatch) {
          setBioGrade(structuredMatch[1]);
          setBioBuilding(structuredMatch[2]);
          setBioInterests(structuredMatch[3]);
        } else if (bioStr) {
          setBioLegacy(bioStr);
        }
        setGithubUrl(p.github_url ?? "");
        setPortfolioUrl(p.portfolio_url ?? "");
        setInterests(p.interests ?? []);
        setResumeUrl(p.resume_url ?? "");
        if (p.resume_url) {
          setResumeFile("resume.pdf");
        }
        setLocation(p.location ?? "");
      })
      .catch(() => {
        // leave defaults
      })
      .finally(() => {
        setProfileLoading(false);
      });

    getGmailStatus()
      .then((status) => setGmail(status))
      .catch(() => {});

    fetchRepos()
      .then((r) => setRepos(r))
      .catch(() => {});
  }, [authenticated]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);

    try {
      await updateProfile({
        school: school || null,
        grad_year: gradYear ? Number(gradYear) : null,
        bio: (() => {
          const concatenatedBio =
            bioLegacy !== null
              ? bioLegacy
              : bioGrade || bioBuilding || bioInterests
                ? `I'm a ${bioGrade}. ${bioBuilding}. I'm interested in ${bioInterests}.`
                : null;
          return concatenatedBio;
        })(),
        github_url: githubUrl || null,
        portfolio_url: portfolioUrl || null,
        location: location || null,
        interests,
      });

      setSaved(true);

      if (savedTimeoutRef.current !== undefined) {
        clearTimeout(savedTimeoutRef.current);
      }
      savedTimeoutRef.current = setTimeout(() => {
        setSaved(false);
      }, 2000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleConnectGmail() {
    setGmailLoading(true);
    try {
      const { url } = await getGmailAuthUrl();
      window.location.href = url;
    } catch {
      setSaveError("Failed to get Gmail auth URL");
      setGmailLoading(false);
    }
  }

  async function handleDisconnectGmail() {
    setGmailLoading(true);
    try {
      await disconnectGmail();
      setGmail({ connected: false, gmail_email: null });
    } catch {
      setSaveError("Failed to disconnect Gmail");
    } finally {
      setGmailLoading(false);
    }
  }

  async function handleSummarizeRepo() {
    const url = repoUrl.trim();
    if (!url) return;

    setRepoLoading(true);
    setRepoError(null);
    try {
      const repo = await createRepo(url);
      setRepos((prev) => [...prev, repo]);
      setRepoUrl("");
      if (repo.warning) {
        setRepoError(repo.warning);
      }
    } catch (err) {
      setRepoError(err instanceof Error ? err.message : "Failed to summarize repo");
    } finally {
      setRepoLoading(false);
    }
  }

  async function handleDeleteRepo(repoId: number) {
    try {
      await deleteRepo(repoId);
      setRepos((prev) => prev.filter((r) => r.id !== repoId));
    } catch (err) {
      setRepoError(err instanceof Error ? err.message : "Failed to remove repo");
    }
  }

  async function handleResumeUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setResumeError("Only PDF files are accepted.");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setResumeError("File too large. Maximum size is 2MB.");
      return;
    }

    setResumeUploading(true);
    setResumeError(null);
    try {
      const result = await uploadResume(file);
      setResumeUrl(result.resume_url);
      setResumeFile(file.name);
    } catch (err) {
      setResumeError(err instanceof Error ? err.message : "Failed to upload resume");
    } finally {
      setResumeUploading(false);
    }
  }

  async function handleResumeDelete() {
    try {
      await deleteResume();
      setResumeUrl("");
      setResumeFile(null);
    } catch (err) {
      setResumeError(err instanceof Error ? err.message : "Failed to remove resume");
    }
  }

  if (authLoading || profileLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  const isFree = !profile || profile.tier === "free";

  return (
    <main className="page-enter mx-auto max-w-2xl px-6 py-10">
      <div className="flex flex-col gap-10">

        {/* Section 1: Account Info */}
        <section className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <p className="text-primary font-medium">
              {profile?.email ?? "—"}
            </p>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                isFree
                  ? "bg-accent/10 text-accent"
                  : "bg-accent text-white"
              }`}
            >
              {isFree ? "free" : "unlocked"}
            </span>
          </div>

          {isFree && (
            <p className="text-sm text-secondary">
              Complete your profile to unlock unlimited briefs.
            </p>
          )}
        </section>

        {/* Section 2: Gmail */}
        <section className="flex flex-col gap-3">
          <h2 className="font-display text-2xl text-primary">Gmail</h2>
          {gmail.connected ? (
            <div className="flex items-center justify-between rounded-lg border border-card-border bg-card px-4 py-3">
              <div>
                <p className="text-sm font-medium text-primary">{gmail.gmail_email}</p>
                <p className="text-xs text-secondary">Connected — emails will send from this account</p>
              </div>
              <button
                type="button"
                onClick={handleDisconnectGmail}
                disabled={gmailLoading}
                className="text-sm text-red-500 hover:text-red-600 disabled:opacity-40"
              >
                Disconnect
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between rounded-lg border border-dashed border-card-border px-4 py-3">
              <p className="text-sm text-secondary">
                Connect Gmail to send emails directly from REACH
              </p>
              <button
                type="button"
                onClick={handleConnectGmail}
                disabled={gmailLoading}
                className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent/90 disabled:opacity-40"
              >
                {gmailLoading ? "Connecting..." : "Connect"}
              </button>
            </div>
          )}
        </section>

        {/* Section 3: Interests */}
        <section className="flex flex-col gap-3">
          <h2 className="font-display text-2xl text-primary">Interests</h2>
          <InterestPicker
            selected={interests}
            onChange={setInterests}
          />
        </section>

        {/* Section: Projects (GitHub Repos) */}
        <section className="flex flex-col gap-3">
          <h2 className="font-display text-2xl text-primary">Projects</h2>
          <p className="text-xs text-tertiary">
            Projects that relate to a founder's domain make your email stand out.
            A trading bot for a fintech founder, a scraper for a data company — that's what gets replies.
          </p>

          {repos.map((repo) => (
            <div key={repo.id} className="rounded-lg border border-card-border bg-card px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-primary truncate">{repo.repo_name}</p>
                    {repo.language && (
                      <span className="text-xs text-tertiary">{repo.language}</span>
                    )}
                    {repo.stars > 0 && (
                      <span className="text-xs text-tertiary">{repo.stars} stars</span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-secondary">{repo.summary}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteRepo(repo.id)}
                  className="text-xs text-red-500 hover:text-red-600 shrink-0"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}

          {repos.length < 3 && (
            <div className="flex gap-2">
              <input
                type="url"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/username/project"
                className="flex-1 rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
              />
              <button
                type="button"
                onClick={handleSummarizeRepo}
                disabled={repoLoading || !repoUrl.trim()}
                className="rounded-lg border border-card-border bg-card px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-background disabled:opacity-40"
              >
                {repoLoading ? "Summarizing..." : "Summarize"}
              </button>
            </div>
          )}

          {repoError && (
            <p className="text-xs text-red-500">{repoError}</p>
          )}
        </section>

        {/* Section 4: Profile Details */}
        <section className="flex flex-col gap-4">
          <h2 className="font-display text-2xl text-primary">Profile Details</h2>

          <form onSubmit={handleSave} className="flex flex-col gap-4">
            {/* School */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="school" className="text-sm font-medium text-secondary">
                School
              </label>
              <input
                id="school"
                type="text"
                value={school}
                onChange={(e) => setSchool(e.target.value)}
                placeholder="e.g. Stanford University"
                className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            {/* Location */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="location" className="text-sm font-medium text-secondary">
                Location
              </label>
              <input
                id="location"
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. San Francisco, New York, Austin..."
                className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            {/* Graduation Year */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="grad_year" className="text-sm font-medium text-secondary">
                Graduation Year
              </label>
              <input
                id="grad_year"
                type="number"
                value={gradYear}
                onChange={(e) => setGradYear(e.target.value)}
                placeholder="e.g. 2026"
                min={2020}
                max={2035}
                className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            {/* Bio Builder */}
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-secondary">About You</label>
                <p className="text-xs text-tertiary">
                  Founders skim — make each line specific, not generic.
                </p>
              </div>

              {bioLegacy !== null ? (
                <div className="flex flex-col gap-2">
                  <textarea
                    rows={3}
                    value={bioLegacy}
                    onChange={(e) => setBioLegacy(e.target.value)}
                    placeholder="A short intro about yourself..."
                    className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent resize-none"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setBioLegacy(null);
                      setBioGrade("");
                      setBioBuilding("");
                      setBioInterests("");
                    }}
                    className="self-start text-xs text-accent hover:underline"
                  >
                    Switch to guided bio builder
                  </button>
                </div>
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-col gap-1">
                    <label htmlFor="bio_grade" className="text-xs font-medium text-tertiary">
                      Grade & School
                    </label>
                    <input
                      id="bio_grade"
                      type="text"
                      value={bioGrade}
                      onChange={(e) => setBioGrade(e.target.value)}
                      placeholder="e.g. Junior at Lincoln High"
                      className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                    {bioGrade && bioWordCount(bioGrade) < 5 && (
                      <p className="text-xs text-amber-500">Be a bit more specific</p>
                    )}
                  </div>

                  <div className="flex flex-col gap-1">
                    <label htmlFor="bio_building" className="text-xs font-medium text-tertiary">
                      What are you building or learning?
                    </label>
                    <input
                      id="bio_building"
                      type="text"
                      value={bioBuilding}
                      onChange={(e) => setBioBuilding(e.target.value)}
                      placeholder="e.g. Writing Python scrapers, learning React"
                      className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                    {bioBuilding && bioWordCount(bioBuilding) < 5 && (
                      <p className="text-xs text-amber-500">Be a bit more specific</p>
                    )}
                    {bioBuilding && bioWordCount(bioBuilding) >= 5 && !hasSpecificTerm(bioBuilding) && (
                      <p className="text-xs text-amber-500">Try mentioning a specific tool, language, or project</p>
                    )}
                  </div>

                  <div className="flex flex-col gap-1">
                    <label htmlFor="bio_interests" className="text-xs font-medium text-tertiary">
                      What problems interest you?
                    </label>
                    <input
                      id="bio_interests"
                      type="text"
                      value={bioInterests}
                      onChange={(e) => setBioInterests(e.target.value)}
                      placeholder="e.g. How startups use NLP to process messy data"
                      className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
                    />
                    {bioInterests && bioWordCount(bioInterests) < 5 && (
                      <p className="text-xs text-amber-500">Be a bit more specific</p>
                    )}
                    {bioInterests && bioWordCount(bioInterests) >= 5 && !hasSpecificTerm(bioInterests) && (
                      <p className="text-xs text-amber-500">Try mentioning a specific tool, language, or project</p>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* GitHub URL */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="github_url" className="text-sm font-medium text-secondary">
                GitHub URL
              </label>
              <input
                id="github_url"
                type="url"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/username"
                className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            {/* Portfolio URL */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="portfolio_url" className="text-sm font-medium text-secondary">
                Portfolio URL
              </label>
              <input
                id="portfolio_url"
                type="url"
                value={portfolioUrl}
                onChange={(e) => setPortfolioUrl(e.target.value)}
                placeholder="https://yoursite.com"
                className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>

            {/* Resume PDF */}
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-secondary">
                Resume (PDF)
              </label>
              <p className="text-xs text-tertiary">
                Upload your resume — it'll be linked in your email signature.
              </p>

              {resumeFile ? (
                <div className="flex items-center justify-between rounded-lg border border-card-border bg-card px-4 py-3">
                  <p className="text-sm text-primary">{resumeFile}</p>
                  <button
                    type="button"
                    onClick={handleResumeDelete}
                    className="text-xs text-red-500 hover:text-red-600"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <label className="flex cursor-pointer items-center justify-center rounded-lg border border-dashed border-card-border px-4 py-6 text-sm text-secondary transition-colors hover:border-accent hover:text-primary">
                  <input
                    type="file"
                    accept=".pdf"
                    onChange={handleResumeUpload}
                    className="hidden"
                    disabled={resumeUploading}
                  />
                  {resumeUploading ? "Uploading..." : "Click to upload or drag and drop"}
                </label>
              )}

              {resumeError && (
                <p className="text-xs text-red-500">{resumeError}</p>
              )}
            </div>

            {/* Save row */}
            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-accent px-5 py-2 text-sm font-medium text-white transition-opacity disabled:opacity-40"
              >
                {saving ? "Saving..." : "Save"}
              </button>

              {saved && (
                <span className="text-sm text-reach-high">Saved</span>
              )}
              {saveError && (
                <span className="text-sm text-red-600">{saveError}</span>
              )}
            </div>
          </form>
        </section>

      </div>
    </main>
  );
}
