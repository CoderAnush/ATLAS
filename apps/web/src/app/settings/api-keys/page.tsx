"use client";

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type ApiKey = {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
};

export default function ApiKeysPage() {
  const { authFetch } = useAuth();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [name, setName] = useState("ci-key");
  const [createdRaw, setCreatedRaw] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const res = await authFetch("/v1/api-keys");
    if (res.ok) setKeys((await res.json()) as ApiKey[]);
  }

  useEffect(() => {
    void load();
  }, []);

  async function createKey(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const res = await authFetch("/v1/api-keys", {
      method: "POST",
      body: JSON.stringify({ name, scopes: [] }),
    });
    if (!res.ok) {
      setError("Unable to create API key (need apikey:manage permission).");
      return;
    }
    const data = await res.json();
    setCreatedRaw(data.api_key);
    setName("ci-key");
    await load();
  }

  async function revoke(id: string) {
    await authFetch(`/v1/api-keys/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">API keys</h2>
        <p className="mt-2 text-atlas-muted">
          Keys are hashed at rest. The raw secret is shown once on creation.
        </p>
      </div>
      <form onSubmit={createKey} className="flex gap-2 rounded-2xl border border-atlas-line bg-atlas-panel p-4">
        <input
          className="flex-1 rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button type="submit" className="rounded-md bg-atlas-accent px-3 py-2 text-white">
          Create
        </button>
      </form>
      {createdRaw ? (
        <p className="rounded-md border border-atlas-line bg-atlas-bg p-3 font-mono text-sm break-all">
          {createdRaw}
        </p>
      ) : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <ul className="space-y-2">
        {keys.map((key) => (
          <li
            key={key.id}
            className="flex items-center justify-between rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
          >
            <div>
              <p className="font-medium">{key.name}</p>
              <p className="text-sm text-atlas-muted">{key.prefix}…</p>
            </div>
            <button
              type="button"
              className="text-sm text-red-700"
              onClick={() => void revoke(key.id)}
            >
              Revoke
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
