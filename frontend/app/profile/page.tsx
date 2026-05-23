"use client";

import { useState, useEffect, useRef } from "react";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchProfile, updateProfile } from "@/lib/api";
import type { UserProfile } from "@/lib/types";
import SkillPicker from "@/components/SkillPicker";

export default function ProfilePage() {
  const { authenticated, loading: authLoading } = useRequireAuth();

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);

  // Form fields
  const [school, setSchool] = useState("");
  const [gradYear, setGradYear] = useState("");
  const [bio, setBio] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [skills, setSkills] = useState<string[]>([]);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const skillsDebounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);
  const savedTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (!authenticated) return;

    fetchProfile()
      .then((p) => {
        setProfile(p);
        setSchool(p.school ?? "");
        setGradYear(p.grad_year != null ? String(p.grad_year) : "");
        setBio(p.bio ?? "");
        setGithubUrl(p.github_url ?? "");
        setPortfolioUrl(p.portfolio_url ?? "");
        setSkills(p.skills ?? []);
      })
      .catch(() => {
        // leave defaults
      })
      .finally(() => {
        setProfileLoading(false);
      });
  }, [authenticated]);

  function handleSkillsChange(newSkills: string[]) {
    setSkills(newSkills);

    if (skillsDebounceRef.current !== undefined) {
      clearTimeout(skillsDebounceRef.current);
    }

    skillsDebounceRef.current = setTimeout(() => {
      updateProfile({ skills: newSkills }).catch(() => {});
    }, 500);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);

    try {
      await updateProfile({
        school: school || null,
        grad_year: gradYear ? Number(gradYear) : null,
        bio: bio || null,
        github_url: githubUrl || null,
        portfolio_url: portfolioUrl || null,
      });

      setSaved(true);

      if (savedTimeoutRef.current !== undefined) {
        clearTimeout(savedTimeoutRef.current);
      }
      savedTimeoutRef.current = setTimeout(() => {
        setSaved(false);
      }, 2000);
    } catch {
      // silently fail for now
    } finally {
      setSaving(false);
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
    <main className="mx-auto max-w-2xl px-6 py-10">
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

        {/* Section 2: Skills */}
        <section className="flex flex-col gap-3">
          <h2 className="font-display text-2xl text-primary">Skills</h2>
          <SkillPicker selected={skills} onChange={handleSkillsChange} />
        </section>

        {/* Section 3: Profile Details */}
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

            {/* Bio */}
            <div className="flex flex-col gap-1.5">
              <label htmlFor="bio" className="text-sm font-medium text-secondary">
                Bio
              </label>
              <textarea
                id="bio"
                rows={3}
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder="A short intro about yourself…"
                className="rounded-lg border border-card-border bg-card px-3 py-2 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent resize-none"
              />
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
            </div>
          </form>
        </section>

      </div>
    </main>
  );
}
