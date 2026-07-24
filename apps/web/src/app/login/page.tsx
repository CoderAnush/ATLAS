"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <p className="font-display text-4xl font-bold text-atlas-ink">ATLAS</p>
      <h1 className="mt-2 text-2xl text-atlas-ink">Sign in</h1>
      <p className="mt-2 text-sm text-atlas-muted">Access your organization workspace.</p>
      <form onSubmit={onSubmit} className="mt-8 space-y-4 rounded-2xl border border-atlas-line bg-atlas-panel p-6">
        <label className="block text-sm">
          Email
          <input
            className="mt-1 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          Password
          <input
            className="mt-1 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-atlas-accent px-3 py-2 text-white disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-atlas-muted">
        No account? <Link href="/register">Create one</Link> ·{" "}
        <Link href="/forgot-password">Forgot password</Link>
      </p>
    </div>
  );
}
