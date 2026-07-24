"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Dataset = {
  id: string;
  name: string;
  status: string;
  current_version: number;
};

export default function ProfilingIndexPage() {
  const { authFetch } = useAuth();
  const [items, setItems] = useState<Dataset[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await authFetch("/v1/datasets?limit=50");
    if (res.ok) {
      const body = (await res.json()) as { items: Dataset[] };
      setItems(body.items.filter((d) => d.status === "ready"));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function run(datasetId: string) {
    setBusy(datasetId);
    setMessage(null);
    const res = await authFetch(`/v1/profiling/run/${datasetId}`, { method: "POST" });
    if (!res.ok) {
      setMessage((await res.json()).detail || "Failed to start profiling");
      setBusy(null);
      return;
    }
    const body = (await res.json()) as { job_id: string };
    setMessage(`Profiling job ${body.job_id} started`);
    setBusy(null);
  }

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Dataset profiling</h2>
        <p className="mt-2 text-atlas-muted">
          Run the Dataset Understanding Agent to profile ready datasets asynchronously.
        </p>
      </div>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}
      <ul className="space-y-2">
        {items.map((ds) => (
          <li
            key={ds.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
          >
            <div>
              <p className="font-medium">{ds.name}</p>
              <p className="text-sm text-atlas-muted">v{ds.current_version}</p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={busy === ds.id}
                onClick={() => void run(ds.id)}
                className="rounded-md bg-atlas-accent px-3 py-2 text-white disabled:opacity-40"
              >
                {busy === ds.id ? "Starting…" : "Run profiling"}
              </button>
              <Link
                href={`/profiling/${ds.id}`}
                className="rounded-md border border-atlas-line px-3 py-2"
              >
                Open report
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
