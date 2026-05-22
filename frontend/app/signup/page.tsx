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
