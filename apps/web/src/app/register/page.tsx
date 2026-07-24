"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    organization_name: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register(form);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-10">
      <p className="font-display text-4xl font-bold text-atlas-ink">ATLAS</p>
      <h1 className="mt-2 text-2xl text-atlas-ink">Create account</h1>
      <p className="mt-2 text-sm text-atlas-muted">
        Registers you as organization owner with full RBAC privileges.
      </p>
      <form onSubmit={onSubmit} className="mt-8 space-y-4 rounded-2xl border border-atlas-line bg-atlas-panel p-6">
        {(
          [
            ["full_name", "Full name", "text"],
            ["email", "Email", "email"],
            ["organization_name", "Organization", "text"],
            ["password", "Password", "password"],
          ] as const
        ).map(([key, label, type]) => (
          <label key={key} className="block text-sm">
            {label}
            <input
              className="mt-1 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
              type={type}
              required
              value={form[key]}
              onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))}
            />
          </label>
        ))}
        <p className="text-xs text-atlas-muted">
          Password: 10+ chars with upper, lower, digit, and symbol.
        </p>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-atlas-accent px-3 py-2 text-white disabled:opacity-60"
        >
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-sm text-atlas-muted">
        Already registered? <Link href="/login">Sign in</Link>
      </p>
    </div>
  );
}
