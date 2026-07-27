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

type FeatureSet = {
  id: string;
  name: string;
  dataset_id: string;
  status: string;
  summary: string;
  quality_score: number;
  rows: number;
  columns: number;
  created_at: string;
};

export default function FeaturesIndexPage() {
  const { authFetch } = useAuth();
  const [items, setItems] = useState<Dataset[]>([]);
  const [featureSets, setFeatureSets] = useState<FeatureSet[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const res = await authFetch("/v1/datasets?limit=50");
    if (res.ok) {
      const body = (await res.json()) as { items: Dataset[] };
      setItems(body.items.filter((d) => d.status === "ready"));
    }

    const fsRes = await authFetch("/v1/features");
    if (fsRes.ok) {
      const body = await fsRes.json();
      if (Array.isArray(body)) {
        setFeatureSets(body as FeatureSet[]);
      }
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function run(datasetId: string) {
    setBusy(datasetId);
    setMessage(null);
    const res = await authFetch(`/v1/features/run/${datasetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: {} }),
    });
    if (!res.ok) {
      setMessage((await res.json()).detail || "Failed to start feature engineering");
      setBusy(null);
      return;
    }
    const body = (await res.json()) as { job_id: string };
    setMessage(`Feature job ${body.job_id} started — open the detail page to review`);
    setBusy(null);
  }

  async function search() {
    if (!searchQuery.trim()) {
      void load();
      return;
    }
    const res = await authFetch("/v1/features/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: searchQuery.trim(), limit: 50 }),
    });
    if (res.ok) {
      const body = await res.json();
      if (Array.isArray(body)) {
        setFeatureSets(body as FeatureSet[]);
      }
    }
  }

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Feature engineering</h2>
        <p className="mt-2 text-atlas-muted">
          Generate feature pipelines from ready datasets. Nothing is applied until you approve.
        </p>
      </div>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}

      <div>
        <h3 className="font-display text-xl text-atlas-ink">Ready datasets</h3>
        <ul className="mt-3 space-y-2">
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
                  {busy === ds.id ? "Starting…" : "Run feature engineering"}
                </button>
                <Link
                  href={`/features/${ds.id}`}
                  className="rounded-md border border-atlas-line px-3 py-2"
                >
                  Open detail
                </Link>
              </div>
            </li>
          ))}
          {items.length === 0 ? (
            <p className="text-atlas-muted">No ready datasets. Upload and profile data first.</p>
          ) : null}
        </ul>
      </div>

      <div>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h3 className="font-display text-xl text-atlas-ink">Feature store</h3>
          <div className="flex gap-2">
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void search();
              }}
              placeholder="Search feature sets…"
              className="rounded-md border border-atlas-line bg-atlas-bg px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={() => void search()}
              className="rounded-md border border-atlas-line px-3 py-2 text-sm"
            >
              Search
            </button>
          </div>
        </div>
        <ul className="mt-3 space-y-2">
          {featureSets.map((fs) => (
            <li
              key={fs.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
            >
              <div>
                <p className="font-medium">{fs.name}</p>
                <p className="text-sm text-atlas-muted">
                  {fs.status} · quality {fs.quality_score.toFixed(1)} · {fs.rows}×{fs.columns}
                </p>
                <p className="text-sm text-atlas-muted">{fs.summary}</p>
              </div>
              <Link
                href={`/features/${fs.dataset_id}`}
                className="rounded-md border border-atlas-line px-3 py-2 text-sm"
              >
                View
              </Link>
            </li>
          ))}
          {featureSets.length === 0 ? (
            <p className="text-atlas-muted">No feature sets yet.</p>
          ) : null}
        </ul>
      </div>
    </section>
  );
}
