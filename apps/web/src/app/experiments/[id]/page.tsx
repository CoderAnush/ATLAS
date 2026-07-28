"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";

type Experiment = {
  id: string;
  name: string;
  description: string;
  status: string;
  algorithm: string | null;
  best_metric_name: string | null;
  best_metric_value: number | null;
  run_count: number;
};

type Run = {
  id: string;
  name: string;
  status: string;
  algorithm: string | null;
  primary_metric: string | null;
  primary_metric_value: number | null;
  runtime_seconds: number | null;
  metrics_json: Record<string, number>;
  hyperparameters_json: Record<string, unknown>;
  visualizations_json: Record<string, unknown>;
  created_at: string;
};

export default function ExperimentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { authFetch } = useAuth();
  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [history, setHistory] = useState<{ event: string; message: string; created_at: string }[]>(
    [],
  );
  const [tags, setTags] = useState<{ key: string; value: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const res = await authFetch(`/v1/experiments/${id}`);
      if (!res.ok) {
        setError(await res.text());
        return;
      }
      const data = await res.json();
      setExperiment(data.experiment);
      setRuns(data.runs || []);
      setHistory(data.history || []);
      setTags(data.tags || []);
    }
    void load();
  }, [authFetch, id]);

  const metricBars = useMemo(() => {
    const first = runs[0];
    if (!first) return [];
    return Object.entries(first.metrics_json || {})
      .filter(([, v]) => typeof v === "number")
      .slice(0, 8)
      .map(([label, value]) => ({ label, value: Number(value) }));
  }, [runs]);

  async function archive() {
    const res = await authFetch("/v1/experiments/archive", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ experiment_id: id }),
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    setExperiment((prev) => (prev ? { ...prev, status: "archived" } : prev));
  }

  async function cloneExp() {
    const res = await authFetch("/v1/experiments/clone", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ experiment_id: id }),
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    const cloned = await res.json();
    window.location.href = `/experiments/${cloned.id}`;
  }

  async function exportExp() {
    const res = await authFetch("/v1/experiments/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ experiment_id: id }),
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    const data = await res.json();
    if (data.download_url) window.open(data.download_url, "_blank");
  }

  if (!experiment) {
    return <div className="p-6 text-atlas-muted">{error || "Loading experiment…"}</div>;
  }

  return (
    <div className="space-y-8 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/experiments" className="text-sm text-atlas-muted underline">
            ← Experiments
          </Link>
          <h1 className="mt-2 font-display text-4xl font-bold text-atlas-ink">{experiment.name}</h1>
          <p className="mt-2 max-w-3xl text-atlas-muted">{experiment.description}</p>
          <p className="mt-2 text-sm text-atlas-muted">
            {experiment.algorithm || "—"} · {experiment.status} · {experiment.run_count} runs · best{" "}
            {experiment.best_metric_name}={experiment.best_metric_value ?? "—"}
          </p>
          <p className="mt-2 text-sm text-atlas-muted">
            Tags: {tags.length ? tags.map((t) => `${t.key}=${t.value}`).join(", ") : "none"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="rounded border border-atlas-line px-3 py-2 text-sm" onClick={() => void cloneExp()}>
            Clone
          </button>
          <button className="rounded border border-atlas-line px-3 py-2 text-sm" onClick={() => void exportExp()}>
            Export
          </button>
          <button className="rounded border border-atlas-line px-3 py-2 text-sm" onClick={() => void archive()}>
            Archive
          </button>
        </div>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">Metrics</h2>
          <div className="space-y-2">
            {metricBars.map((item) => (
              <div key={item.label} className="grid grid-cols-[140px_1fr_56px] gap-2 text-sm">
                <span className="text-atlas-muted">{item.label}</span>
                <div className="h-2 rounded bg-atlas-line">
                  <div
                    className="h-2 rounded bg-atlas-ink"
                    style={{ width: `${Math.min(100, Math.abs(item.value) * 100)}%` }}
                  />
                </div>
                <span className="text-right tabular-nums">{item.value.toFixed(3)}</span>
              </div>
            ))}
          </div>
          <h2 className="pt-4 text-xl font-semibold">Runs</h2>
          <ul className="space-y-2">
            {runs.map((run) => (
              <li key={run.id} className="border border-atlas-line p-3">
                <p className="font-medium">{run.name}</p>
                <p className="text-sm text-atlas-muted">
                  {run.status} · {run.primary_metric}={run.primary_metric_value ?? "—"} ·{" "}
                  {run.runtime_seconds?.toFixed(2) ?? "—"}s
                </p>
                <pre className="mt-2 max-h-40 overflow-auto text-xs">
                  {JSON.stringify(
                    {
                      metrics: run.metrics_json,
                      hyperparameters: run.hyperparameters_json,
                      visualizations: run.visualizations_json,
                    },
                    null,
                    2,
                  )}
                </pre>
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-3">
          <h2 className="text-xl font-semibold">History</h2>
          <ul className="space-y-2 text-sm">
            {history.map((item, idx) => (
              <li key={`${item.event}-${idx}`} className="border-b border-atlas-line py-2">
                <p className="font-medium">{item.event}</p>
                <p className="text-atlas-muted">{item.message || "—"}</p>
                <p className="text-xs text-atlas-muted">{new Date(item.created_at).toLocaleString()}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
