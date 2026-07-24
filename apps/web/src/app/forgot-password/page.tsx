"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/v1/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      setMessage(data.detail || "If the account exists, a reset email will be sent.");
    } catch {
      setMessage("Unable to reach the API.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <p className="font-display text-4xl font-bold text-atlas-ink">ATLAS</p>
      <h1 className="mt-2 text-2xl text-atlas-ink">Forgot password</h1>
      <p className="mt-2 text-sm text-atlas-muted">
        Mail delivery is stubbed in Phase 2; the reset architecture is in place.
      </p>
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
        {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-atlas-accent px-3 py-2 text-white disabled:opacity-60"
        >
          {busy ? "Submitting…" : "Request reset"}
        </button>
      </form>
      <p className="mt-4 text-sm text-atlas-muted">
        <Link href="/login">Back to sign in</Link>
      </p>
    </div>
  );
}
