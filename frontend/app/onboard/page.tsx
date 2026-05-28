"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useRequireAuth } from "@/lib/useAuth";
import { fetchProfile, updateProfile } from "@/lib/api";
import InterestPicker from "@/components/InterestPicker";

export default function OnboardPage() {
  const { authenticated, loading: authLoading } = useRequireAuth();
  const router = useRouter();

  const [profileLoading, setProfileLoading] = useState(true);
  const [step, setStep] = useState<"interests" | "location">("interests");
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [location, setLocation] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!authenticated) return;

    fetchProfile()
      .then((profile) => {
        if (profile.interests && profile.interests.length > 0) {
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
        interests: selectedInterests,
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
        {step === "interests" && (
          <>
            <div className="flex flex-col gap-2">
              <h1 className="font-display text-4xl text-primary">
                What domains excite you?
              </h1>
              <p className="text-secondary">
                Pick up to 2 domains so we can match you with founders building in those areas.
              </p>
            </div>

            <InterestPicker
              selected={selectedInterests}
              onChange={setSelectedInterests}
            />

            <div className="flex flex-col items-start gap-3 pt-2">
              <button
                type="button"
                onClick={() => setStep("location")}
                disabled={selectedInterests.length === 0}
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
