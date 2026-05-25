"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchProfile, updateProfile } from "@/lib/api";
import CapabilityPicker from "@/components/CapabilityPicker";
import type { Tier1Key } from "@/lib/capabilities";

export default function OnboardPage() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const router = useRouter();

  const [profileLoading, setProfileLoading] = useState(true);
  const [step, setStep] = useState<"capabilities" | "location">("capabilities");
  const [selectedTier1, setSelectedTier1] = useState<Tier1Key[]>([]);
  const [selectedTier2, setSelectedTier2] = useState<string[]>([]);
  const [location, setLocation] = useState("");
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

  async function handleFinish() {
    setSaving(true);
    try {
      await updateProfile({
        skills: selectedTier2,
        location: location.trim() || null,
      });
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
        {step === "capabilities" && (
          <>
            <div className="flex flex-col gap-2">
              <h1 className="font-display text-4xl text-primary">
                What are you good at?
              </h1>
              <p className="text-secondary">
                Pick your focus areas so we can match you with the right
                founders.
              </p>
            </div>

            <CapabilityPicker
              selectedTier1={selectedTier1}
              selectedTier2={selectedTier2}
              onChangeTier1={setSelectedTier1}
              onChangeTier2={setSelectedTier2}
            />

            <div className="flex flex-col items-start gap-3 pt-2">
              <button
                type="button"
                onClick={() => setStep("location")}
                disabled={selectedTier2.length === 0}
                className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-opacity disabled:opacity-40"
              >
                Continue
              </button>

              <button
                type="button"
                onClick={() => router.push("/feed")}
                className="text-sm text-tertiary underline-offset-2 hover:underline"
              >
                Skip for now
              </button>
            </div>
          </>
        )}

        {step === "location" && (
          <>
            <div className="flex flex-col gap-2">
              <h1 className="font-display text-4xl text-primary">
                Where are you based?
              </h1>
              <p className="text-secondary">
                Founders near you are more likely to meet in person.
              </p>
            </div>

            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. San Francisco, New York, Austin..."
              className="rounded-lg border border-card-border bg-card px-3 py-2.5 text-sm text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent"
            />

            <div className="flex flex-col items-start gap-3 pt-2">
              <button
                type="button"
                onClick={handleFinish}
                disabled={saving}
                className="rounded-lg bg-accent px-6 py-2.5 text-sm font-medium text-white transition-opacity disabled:opacity-40"
              >
                {saving ? "Saving..." : "Finish"}
              </button>

              <button
                type="button"
                onClick={handleFinish}
                className="text-sm text-tertiary underline-offset-2 hover:underline"
              >
                Skip location
              </button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
