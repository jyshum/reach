"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { submitGmailCallback } from "@/lib/api";

export default function GmailCallbackPage() {
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
        setError(err.message || "Failed to connect Gmail.");
      });
  }, [searchParams, router]);

  return (
    <div className="min-h-[100dvh] flex items-center justify-center">
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
    </div>
  );
}
