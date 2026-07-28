"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";

type Experiment = {
  id: string;
  name: string;
  status: string;
  algorithm: string | null;
  best_metric_name: string | null;
  best_metric_value: number | null;
  run_count: number;
  pinned: boolean;
  created_at: string;
};

type Run = {
  id: string;
  experiment_id: string;
  name: string;
  status: string;
  algorithm: string | null;
  primary_metric: string | null;
  primary_metric_value: number | null;
  runtime_seconds: number | null;
  favorite: boolean;
  metrics_json: Record<string, number>;
  created_at: string;
};

type LeaderboardEntry = {
  id: string;
  experiment_id: string;
  run_id: string;
  algorithm: string | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  loss: number | null;
  runtime_seconds: number | null;
  rank_score: number | null;
  created_at: string;
};

function BarChart({ values }: { values: { label: string; value: number }[] }) {
  const max = Math.max(...values.map((v) => Math.abs(v.value)), 0.0001);
  return (
    <div className="space-y-2">
      {values.map((item) => (
        <div key={item.label} className="grid grid-cols-[120px_1fr_48px] items-center gap-2 text-sm">
          <span className="truncate text-atlas-muted">{item.label}</span>
          <div className="h-2 rounded bg-atlas-line">
            <div
              className="h-2 rounded bg-atlas-ink"
              style={{ width: `${Math.max(4, (Math.abs(item.value) / max) * 100)}%` }}
            />
          </div>
          <span className="text-right tabular-nums">{item.value.toFixed(3)}</span>
        </div>
      ))}
    </div>
  );
}

export default function ExperimentsPage() {
  const { authFetch } = useAuth();
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [compare, setCompare] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [exRes, runRes, boardRes] = await Promise.all([
      authFetch("/v1/experiments"),
      authFetch("/v1/experiments/runs"),
      authFetch("/v1/experiments/leaderboard"),
    ]);
    if (!exRes.ok || !runRes.ok || !boardRes.ok) {
      setError("Failed to load experiments");
      return;
    }
    setExperiments(await exRes.json());
    setRuns(await runRes.json());
    setLeaderboard(await boardRes.json());
  }

  useEffect(() => {
    void refresh();
  }, [authFetch]);

  const favorites = useMemo(() => runs.filter((r) => r.favorite), [runs]);
  const pinned = useMemo(() => experiments.filter((e) => e.pinned), [experiments]);
  const chartValues = useMemo(
    () =>
      leaderboard.slice(0, 8).map((row) => ({
        label: row.algorithm || row.run_id.slice(0, 8),
        value: Number(row.rank_score ?? row.accuracy ?? 0),
      })),
    [leaderboard],
  );

  async function search() {
    setBusy(true);
    setError(null);
    try {
      const res = await authFetch("/v1/experiments/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 50 }),
      });
      if (!res.ok) throw new Error(await res.text());
      setExperiments(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "search failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleFavorite(runId: string) {
    const res = await authFetch("/v1/experiments/favorite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: runId }),
    });
    if (res.ok) await refresh();
  }

  async function runCompare() {
    if (selected.length < 2) return;
    setBusy(true);
    try {
      const res = await authFetch("/v1/experiments/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_ids: selected, name: "ui-compare" }),
      });
      if (!res.ok) throw new Error(await res.text());
      setCompare(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "compare failed");
    } finally {
      setBusy(false);
    }
  }

  function toggleSelected(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id].slice(-5)));
  }

  return (
    <div className="space-y-8 p-6">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-atlas-muted">Phase 9</p>
        <h1 className="font-display text-4xl font-bold text-atlas-ink">Experiments</h1>
        <p className="max-w-3xl text-atlas-muted">
          Registry, leaderboard, and run comparison for training and HPO outcomes. Experiments are
          created automatically when jobs complete.
        </p>
      </header>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <section className="flex flex-wrap items-end gap-3">
        <label className="block grow space-y-1">
          <span className="text-sm text-atlas-muted">Search</span>
          <input
            className="w-full rounded border border-atlas-line bg-transparent px-3 py-2"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Name, algorithm, notes…"
          />
        </label>
        <button
          className="rounded bg-atlas-ink px-4 py-2 text-sm text-white disabled:opacity-50"
          disabled={busy}
          onClick={() => void search()}
        >
          Search
        </button>
        <button
          className="rounded border border-atlas-line px-4 py-2 text-sm"
          disabled={busy}
          onClick={() => void refresh()}
        >
          Refresh
        </button>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Leaderboard</h2>
          <BarChart values={chartValues} />
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-atlas-muted">
                <tr>
                  <th className="py-2 pr-3">Algorithm</th>
                  <th className="py-2 pr-3">Accuracy</th>
                  <th className="py-2 pr-3">F1</th>
                  <th className="py-2 pr-3">Runtime</th>
                  <th className="py-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((row) => (
                  <tr key={row.id} className="border-t border-atlas-line">
                    <td className="py-2 pr-3">
                      <Link className="underline" href={`/experiments/${row.experiment_id}`}>
                        {row.algorithm || "—"}
                      </Link>
                    </td>
                    <td className="py-2 pr-3 tabular-nums">{row.accuracy?.toFixed(3) ?? "—"}</td>
                    <td className="py-2 pr-3 tabular-nums">{row.f1?.toFixed(3) ?? "—"}</td>
                    <td className="py-2 pr-3 tabular-nums">{row.runtime_seconds?.toFixed(2) ?? "—"}</td>
                    <td className="py-2">{new Date(row.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Run comparison</h2>
            <button
              className="rounded border border-atlas-line px-3 py-1 text-sm disabled:opacity-50"
              disabled={selected.length < 2 || busy}
              onClick={() => void runCompare()}
            >
              Compare selected ({selected.length})
            </button>
          </div>
          <ul className="space-y-2">
            {runs.slice(0, 20).map((run) => (
              <li key={run.id} className="flex items-center gap-3 border border-atlas-line px-3 py-2">
                <input
                  type="checkbox"
                  checked={selected.includes(run.id)}
                  onChange={() => toggleSelected(run.id)}
                />
                <div className="min-w-0 grow">
                  <Link className="font-medium underline" href={`/experiments/${run.experiment_id}`}>
                    {run.name}
                  </Link>
                  <p className="truncate text-sm text-atlas-muted">
                    {run.algorithm} · {run.primary_metric}={run.primary_metric_value ?? "—"}
                  </p>
                </div>
                <button className="text-sm underline" onClick={() => void toggleFavorite(run.id)}>
                  {run.favorite ? "Favorited" : "Favorite"}
                </button>
              </li>
            ))}
          </ul>
          {compare ? (
            <pre className="max-h-80 overflow-auto rounded border border-atlas-line bg-black/5 p-3 text-xs">
              {JSON.stringify(compare, null, 2)}
            </pre>
          ) : null}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Experiments</h2>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {experiments.map((item) => (
            <Link
              key={item.id}
              href={`/experiments/${item.id}`}
              className="block border border-atlas-line p-4 transition hover:bg-black/5"
            >
              <p className="font-medium">{item.name}</p>
              <p className="mt-1 text-sm text-atlas-muted">
                {item.algorithm || "—"} · {item.run_count} runs · {item.status}
              </p>
              <p className="mt-2 text-sm">
                Best {item.best_metric_name || "metric"}:{" "}
                <span className="tabular-nums">{item.best_metric_value ?? "—"}</span>
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 text-xl font-semibold">Pinned</h2>
          <p className="text-sm text-atlas-muted">
            {pinned.length ? pinned.map((p) => p.name).join(", ") : "No pinned experiments yet."}
          </p>
        </div>
        <div>
          <h2 className="mb-2 text-xl font-semibold">Favorites</h2>
          <p className="text-sm text-atlas-muted">
            {favorites.length ? favorites.map((f) => f.name).join(", ") : "No favorite runs yet."}
          </p>
        </div>
      </section>
    </div>
  );
}
