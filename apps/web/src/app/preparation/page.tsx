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

export default function PreparationIndexPage() {
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
    const res = await authFetch(`/v1/preparation/run/${datasetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strategies: {} }),
    });
    if (!res.ok) {
      setMessage((await res.json()).detail || "Failed to start preparation");
      setBusy(null);
      return;
    }
    const body = (await res.json()) as { job_id: string };
    setMessage(`Cleaning job ${body.job_id} started — open the plan to approve`);
    setBusy(null);
  }

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Data preparation</h2>
        <p className="mt-2 text-atlas-muted">
          Generate a cleaning plan from profiling insights. Nothing is applied until you approve.
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
                {busy === ds.id ? "Starting…" : "Run cleaning"}
              </button>
              <Link
                href={`/preparation/${ds.id}`}
                className="rounded-md border border-atlas-line px-3 py-2"
              >
                Open plan
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
