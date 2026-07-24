"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";

type Summary = {
  rows: number;
  columns: number;
  problem_type: string;
  target_column: string | null;
  target_confidence: number | null;
  health: string;
  quality_overall: number;
  summary: string;
};

type Column = {
  name: string;
  kind: string;
  missing_pct: number;
  unique: number;
  statistics?: { variance?: number };
};

export default function ProfilingDetailPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { authFetch } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [columns, setColumns] = useState<Column[]>([]);
  const [tab, setTab] = useState("overview");
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [sort, setSort] = useState("missing_pct");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setError(null);
    const s = await authFetch(`/v1/profiling/${datasetId}/summary`);
    if (!s.ok) {
      setError("No profile yet — run profiling from the Profiling page.");
      return;
    }
    setSummary((await s.json()) as Summary);
    const p = await authFetch(`/v1/profiling/${datasetId}`);
    if (p.ok) setProfile((await p.json()) as Record<string, unknown>);
    const params = new URLSearchParams({ sort });
    if (q) params.set("q", q);
    if (kind) params.set("kind", kind);
    const c = await authFetch(`/v1/profiling/${datasetId}/statistics?${params}`);
    if (c.ok) setColumns((await c.json()) as Column[]);
  }

  useEffect(() => {
    void load();
  }, [datasetId, sort, kind]);

  const quality = (profile?.quality || {}) as Record<string, unknown>;
  const leakage = (profile?.leakage || { findings: [] }) as {
    findings: Array<{ type: string; column: string; detail: string; severity: string }>;
  };
  const recommendations = (profile?.recommendations || []) as string[];

  const tabs = useMemo(
    () => [
      "overview",
      "summary",
      "columns",
      "statistics",
      "quality",
      "correlation",
      "missing",
      "target",
      "health",
      "recommendations",
    ],
    [],
  );

  async function download(format: string) {
    const res = await authFetch(`/v1/profiling/${datasetId}/download?format=${format}`);
    if (!res.ok) return;
    const body = (await res.json()) as { url: string };
    window.open(body.url, "_blank");
  }

  if (error) {
    return (
      <section className="mx-auto max-w-3xl space-y-4">
        <p className="text-atlas-muted">{error}</p>
        <Link href="/profiling" className="text-atlas-accent">
          ← Back to profiling
        </Link>
      </section>
    );
  }

  if (!summary) return <p className="text-atlas-muted">Loading profile…</p>;

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/profiling" className="text-sm text-atlas-accent">
            ← Profiling
          </Link>
          <h2 className="mt-2 font-display text-3xl text-atlas-ink">Dataset understanding</h2>
          <p className="mt-1 text-atlas-muted">
            {summary.rows.toLocaleString()} rows · {summary.columns} columns · health{" "}
            {summary.health}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["json", "markdown", "html", "pdf"] as const).map((fmt) => (
            <button
              key={fmt}
              type="button"
              onClick={() => void download(fmt)}
              className="rounded-md border border-atlas-line px-3 py-1 text-sm"
            >
              {fmt.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded-md px-3 py-1 text-sm ${
              tab === t ? "bg-atlas-accent text-white" : "border border-atlas-line"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "overview" || tab === "summary" ? (
        <div className="whitespace-pre-wrap rounded-xl border border-atlas-line bg-atlas-panel p-4 text-sm leading-relaxed">
          {summary.summary}
        </div>
      ) : null}

      {tab === "health" || tab === "quality" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {Object.entries(quality).map(([k, v]) => (
            <div key={k} className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">{k}</p>
              <p className="mt-1 text-lg font-medium">{String(v)}</p>
            </div>
          ))}
        </div>
      ) : null}

      {tab === "target" ? (
        <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
          <p>
            Target: <strong>{summary.target_column || "—"}</strong>
          </p>
          <p>
            Confidence:{" "}
            {summary.target_confidence != null
              ? `${Math.round(summary.target_confidence * 100)}%`
              : "—"}
          </p>
          <p>Problem type: {summary.problem_type}</p>
        </div>
      ) : null}

      {tab === "recommendations" ? (
        <ul className="list-disc space-y-2 pl-5 text-sm text-atlas-muted">
          {recommendations.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      ) : null}

      {tab === "correlation" ? (
        <pre className="overflow-auto rounded-xl border border-atlas-line bg-atlas-panel p-4 text-xs">
          {JSON.stringify((profile as { correlations?: unknown })?.correlations, null, 2)}
        </pre>
      ) : null}

      {tab === "missing" ? (
        <pre className="overflow-auto rounded-xl border border-atlas-line bg-atlas-panel p-4 text-xs">
          {JSON.stringify(
            (profile as { missing?: { per_column?: unknown } } | null)?.missing?.per_column ??
              profile?.missing,
            null,
            2,
          )}
        </pre>
      ) : null}

      {tab === "columns" || tab === "statistics" ? (
        <div className="space-y-3">
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              className="flex-1 rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
              placeholder="Search columns"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onBlur={() => void load()}
            />
            <select
              className="rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              <option value="">All types</option>
              <option value="integer">integer</option>
              <option value="float">float</option>
              <option value="categorical">categorical</option>
              <option value="text">text</option>
              <option value="datetime">datetime</option>
              <option value="boolean">boolean</option>
              <option value="id">id</option>
            </select>
            <select
              className="rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="missing_pct">Missing %</option>
              <option value="unique">Unique</option>
              <option value="variance">Variance</option>
              <option value="name">Name</option>
            </select>
          </div>
          <div className="overflow-x-auto rounded-xl border border-atlas-line">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-atlas-panel text-atlas-muted">
                <tr>
                  <th className="px-3 py-2">Column</th>
                  <th className="px-3 py-2">Kind</th>
                  <th className="px-3 py-2">Missing %</th>
                  <th className="px-3 py-2">Unique</th>
                </tr>
              </thead>
              <tbody>
                {columns.map((c) => (
                  <tr key={c.name} className="border-t border-atlas-line">
                    <td className="px-3 py-2">{c.name}</td>
                    <td className="px-3 py-2">{c.kind}</td>
                    <td className="px-3 py-2">{c.missing_pct}</td>
                    <td className="px-3 py-2">{c.unique}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {tab === "overview" ? (
        <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4 text-sm">
          <p>Leakage findings: {leakage.findings?.length || 0}</p>
          <ul className="mt-2 list-disc pl-5 text-atlas-muted">
            {(leakage.findings || []).slice(0, 8).map((f) => (
              <li key={`${f.type}-${f.column}`}>
                [{f.severity}] {f.type}: {f.column} — {f.detail}
              </li>
            ))}
          </ul>
          <Link
            className="mt-4 inline-block text-atlas-accent"
            href={`/datasets/${datasetId}`}
          >
            Open dataset
          </Link>
        </div>
      ) : null}
    </section>
  );
}
