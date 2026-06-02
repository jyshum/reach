"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { submitGmailCallback } from "@/lib/api";

function CallbackHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setStatus("error");
      setError("No authorization code received from Google.");
      return;
    }

    submitGmailCallback(code)
      .then(() => {
        setStatus("success");
        setTimeout(() => router.push("/profile"), 2000);
      })
      .catch((err) => {
        setStatus("error");
        const msg = typeof err === "string" ? err : err?.message || JSON.stringify(err);
        setError(msg || "Failed to connect Gmail.");
        console.error("Gmail callback error:", err);
      });
  }, [searchParams, router]);

  return (
    <div className="text-center max-w-md">
      {status === "loading" && (
        <>
          <h1 className="text-xl font-semibold mb-2">Connecting Gmail...</h1>
          <p className="text-zinc-500">Please wait while we finish setting up.</p>
        </>
      )}
      {status === "success" && (
        <>
          <h1 className="text-xl font-semibold mb-2">Gmail Connected</h1>
          <p className="text-zinc-500">Redirecting you back...</p>
        </>
      )}
      {status === "error" && (
        <>
          <h1 className="text-xl font-semibold mb-2 text-red-600">Connection Failed</h1>
          <p className="text-zinc-500 mb-4">{error}</p>
          <button
            onClick={() => router.push("/profile")}
            className="text-sm text-blue-600 hover:underline"
          >
            Back to profile
          </button>
        </>
      )}
    </div>
  );
}

export default function GmailCallbackPage() {
  return (
    <div className="min-h-[100dvh] flex items-center justify-center">
      <Suspense fallback={<p className="text-zinc-500">Loading...</p>}>
        <CallbackHandler />
      </Suspense>
    </div>
  );
}
