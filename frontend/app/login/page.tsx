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
