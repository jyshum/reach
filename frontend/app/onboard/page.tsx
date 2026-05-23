"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchProfile, updateProfile } from "@/lib/api";
import SkillPicker from "@/components/SkillPicker";

export default function OnboardPage() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const router = useRouter();

  const [profileLoading, setProfileLoading] = useState(true);
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!authenticated) return;

    fetchProfile()
      .then((profile) => {
        if (profile.skills && profile.skills.length > 0) {
          router.replace("/feed");
        } else {
          setProfileLoading(false);
        }
      })
      .catch(() => {
        setProfileLoading(false);
      });
  }, [authenticated, router]);

  async function handleContinue() {
    setSaving(true);
    try {
      await updateProfile({ skills: selected });
    } catch {
      // proceed to feed even if save fails
    } finally {
      setSaving(false);
      router.push("/feed");
    }
  }

  if (authLoading || profileLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-20">
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <h1 className="font-display text-4xl text-primary">
            What are you good at?
          </h1>
          <p className="text-secondary">
            Pick 3–5 skills so we can match you with the right founders.
          </p>
        </div>

        <SkillPicker selected={selected} onChange={setSelected} max={5} />

        <div className="flex flex-col items-start gap-3 pt-2">
          <button
            type="button"
            onClick={handleContinue}
            disabled={selected.length < 3 || saving}
            className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-opacity disabled:opacity-40"
          >
            {saving ? "Saving..." : "Continue"}
          </button>

          <button
            type="button"
            onClick={() => router.push("/feed")}
            className="text-sm text-tertiary underline-offset-2 hover:underline"
          >
            Skip for now
          </button>
        </div>
      </div>
    </main>
  );
}
