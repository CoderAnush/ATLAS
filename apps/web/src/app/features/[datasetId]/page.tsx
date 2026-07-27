"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Summary = {
  dataset_id: string;
  job_id: string;
  status: string;
  summary: string;
  feature_set_id: string | null;
  quality_score: number | null;
  recommendations: Array<{ type?: string; message?: string }> | null;
};

type FeatureSet = {
  id: string;
  job_id: string;
  dataset_id: string;
  name: string;
  status: string;
  summary: string;
  selected_features: unknown[];
  rejected_features: unknown[];
  quality_score: number;
  rows: number;
  columns: number;
  output_dataset_version: number | null;
};

type PipelineStep = Record<string, unknown> & {
  kind?: string;
  columns?: string[] | string;
  params?: Record<string, unknown>;
  approved?: boolean;
};

type ReportPayload = {
  id: string;
  report: {
    applied_steps?: Array<Record<string, unknown>>;
    feature_scores?: Record<string, Record<string, number>>;
    validation?: Record<string, unknown>;
    summary?: Record<string, unknown>;
  };
  graph: {
    correlation_matrix?: { data?: Record<string, Record<string, number>>; shape?: number[] };
    pca_plot?: {
      explained_variance?: number[];
      data?: Record<string, number[]>;
    };
    variance_distribution?: { data?: Record<string, number> };
  };
  recommendations: { recommendations?: Array<{ type?: string; message?: string }> };
};

export default function FeaturesDetailPage() {
  const params = useParams<{ datasetId: string }>();
  const datasetId = params.datasetId;
  const { authFetch } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [featureSet, setFeatureSet] = useState<FeatureSet | null>(null);
  const [report, setReport] = useState<ReportPayload | null>(null);
  const [editedSteps, setEditedSteps] = useState<PipelineStep[] | null>(null);
  const [tab, setTab] = useState<"pipeline" | "features" | "viz" | "recommendations">("pipeline");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [notFound, setNotFound] = useState(false);

  async function load() {
    const res = await authFetch(`/v1/features/dataset/${datasetId}`);
    if (!res.ok) {
      setSummary(null);
      setNotFound(res.status === 404);
      return;
    }
    setNotFound(false);
    const body = (await res.json()) as Summary;
    setSummary(body);

    if (body.feature_set_id) {
      const fsRes = await authFetch(`/v1/features/${body.feature_set_id}`);
      if (fsRes.ok) {
        setFeatureSet((await fsRes.json()) as FeatureSet);
      }

      const rpRes = await authFetch(`/v1/features/report/${body.feature_set_id}`);
      if (rpRes.ok) {
        setReport((await rpRes.json()) as ReportPayload);
      }

      if (editedSteps === null && body.job_id) {
        const expRes = await authFetch("/v1/features/export", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: body.job_id }),
        });
        if (expRes.ok) {
          const exp = (await expRes.json()) as { pipeline?: { steps?: PipelineStep[] } };
          const steps = exp.pipeline?.steps ?? [];
          setEditedSteps(steps.map((s) => ({ ...s, approved: s.approved !== false })));
        }
      }
    }
  }

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 4000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  function toggleStepApproved(idx: number) {
    setEditedSteps((prev) => {
      const steps = [...(prev ?? [])];
      const step = { ...steps[idx] };
      step.approved = step.approved === false;
      steps[idx] = step;
      return steps;
    });
  }

  async function approve() {
    if (!summary) return;
    setBusy(true);
    setMessage(null);
    const res = await authFetch("/v1/features/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: summary.job_id,
        edited_steps: editedSteps ?? undefined,
      }),
    });
    setBusy(false);
    if (!res.ok) {
      setMessage((await res.json()).detail || "Approve failed");
      return;
    }
    setMessage("Approved — feature matrix version created");
    setEditedSteps(null);
    await load();
  }

  async function reject() {
    if (!summary) return;
    setBusy(true);
    setMessage(null);
    const res = await authFetch("/v1/features/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: summary.job_id, reason: "Rejected from UI" }),
    });
    setBusy(false);
    if (!res.ok) {
      setMessage((await res.json()).detail || "Reject failed");
      return;
    }
    setMessage("Rejected — original dataset unchanged");
    await load();
  }

  async function exportJob() {
    if (!summary) return;
    setBusy(true);
    const res = await authFetch("/v1/features/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: summary.job_id }),
    });
    setBusy(false);
    if (!res.ok) {
      setMessage((await res.json()).detail || "Export failed");
      return;
    }
    const body = await res.json();
    setMessage(body.data_url ? `Export ready: ${body.data_url}` : "Pipeline exported");
  }

  const steps = editedSteps ?? [];
  const selected = featureSet?.selected_features ?? [];
  const rejected = featureSet?.rejected_features ?? [];
  const recommendations =
    summary?.recommendations ?? report?.recommendations?.recommendations ?? [];
  const corrData = report?.graph?.correlation_matrix?.data;
  const pcaVariance = report?.graph?.pca_plot?.explained_variance;
  const varianceDist = report?.graph?.variance_distribution?.data;

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-atlas-muted">
            <Link href="/features">Features</Link> / {datasetId}
          </p>
          <h2 className="font-display text-3xl text-atlas-ink">Feature pipeline</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {summary?.status === "awaiting_approval" ? (
            <>
              <button
                type="button"
                disabled={busy}
                onClick={() => void approve()}
                className="rounded-md bg-atlas-accent px-3 py-2 text-white disabled:opacity-40"
              >
                Approve
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void reject()}
                className="rounded-md border border-atlas-line px-3 py-2 disabled:opacity-40"
              >
                Reject
              </button>
            </>
          ) : null}
          {summary ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void exportJob()}
              className="rounded-md border border-atlas-line px-3 py-2 disabled:opacity-40"
            >
              Export
            </button>
          ) : null}
        </div>
      </div>

      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}

      {!summary ? (
        <p className="text-atlas-muted">
          {notFound
            ? "No feature job yet. Start one from the features list."
            : "Loading feature job…"}
        </p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">Status</p>
              <p className="text-lg font-medium">{summary.status}</p>
            </div>
            <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">Quality score</p>
              <p className="text-lg font-medium">
                {summary.quality_score != null ? summary.quality_score.toFixed(1) : "—"}
              </p>
            </div>
            <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">Matrix shape</p>
              <p className="text-lg font-medium">
                {featureSet ? `${featureSet.rows}×${featureSet.columns}` : "—"}
              </p>
            </div>
            <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">Output version</p>
              <p className="text-lg font-medium">
                {featureSet?.output_dataset_version != null
                  ? `v${featureSet.output_dataset_version}`
                  : "—"}
              </p>
            </div>
          </div>

          <p className="text-atlas-muted">{summary.summary}</p>

          <div className="flex flex-wrap gap-2 border-b border-atlas-line pb-2">
            {(
              [
                ["pipeline", "Pipeline"],
                ["features", "Features"],
                ["viz", "Visualizations"],
                ["recommendations", "Recommendations"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={
                  tab === key
                    ? "rounded-md bg-atlas-accent px-3 py-1.5 text-white"
                    : "rounded-md border border-atlas-line px-3 py-1.5"
                }
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "pipeline" ? (
            <ol className="space-y-2">
              {steps.map((step, idx) => {
                const kind = String(step.kind ?? "unknown");
                const cols = step.columns;
                const colLabel = Array.isArray(cols)
                  ? cols.join(", ")
                  : typeof cols === "string"
                    ? cols
                    : "";
                const approved = step.approved !== false;
                return (
                  <li
                    key={idx}
                    className="flex items-start justify-between gap-3 rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
                  >
                    <div>
                      <p className="font-medium">
                        Step {idx + 1} · {kind}
                        {colLabel ? ` · ${colLabel}` : ""}
                      </p>
                      {step.params?.reason ? (
                        <p className="text-sm text-atlas-muted">{String(step.params.reason)}</p>
                      ) : null}
                      {step.params?.disabled ? (
                        <p className="text-sm text-atlas-muted">Disabled (Phase 7)</p>
                      ) : null}
                    </div>
                    {summary.status === "awaiting_approval" && !step.params?.disabled ? (
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={approved}
                          onChange={() => toggleStepApproved(idx)}
                        />
                        Approved
                      </label>
                    ) : (
                      <span className="text-sm text-atlas-muted">
                        {approved ? "approved" : "skipped"}
                      </span>
                    )}
                  </li>
                );
              })}
              {steps.length === 0 ? (
                <p className="text-atlas-muted">Waiting for pipeline generation…</p>
              ) : null}
            </ol>
          ) : null}

          {tab === "features" ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
                <h3 className="mb-2 font-medium">Selected ({selected.length})</h3>
                <ul className="max-h-64 space-y-1 overflow-auto text-sm text-atlas-muted">
                  {selected.map((f, i) => (
                    <li key={i}>{String(f)}</li>
                  ))}
                  {selected.length === 0 ? <li>None yet</li> : null}
                </ul>
              </div>
              <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
                <h3 className="mb-2 font-medium">Rejected ({rejected.length})</h3>
                <ul className="max-h-64 space-y-1 overflow-auto text-sm text-atlas-muted">
                  {rejected.map((f, i) => (
                    <li key={i}>{String(f)}</li>
                  ))}
                  {rejected.length === 0 ? <li>None</li> : null}
                </ul>
              </div>
            </div>
          ) : null}

          {tab === "viz" ? (
            <div className="space-y-4">
              {corrData ? (
                <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
                  <h3 className="mb-2 font-medium">Correlation matrix</h3>
                  <div className="overflow-auto">
                    <table className="min-w-full text-xs">
                      <thead>
                        <tr>
                          <th className="px-2 py-1 text-left" />
                          {Object.keys(corrData).map((col) => (
                            <th key={col} className="px-2 py-1 text-left">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(corrData).map(([row, vals]) => (
                          <tr key={row}>
                            <td className="px-2 py-1 font-medium">{row}</td>
                            {Object.keys(corrData).map((col) => (
                              <td key={col} className="px-2 py-1 text-atlas-muted">
                                {vals[col] != null ? Number(vals[col]).toFixed(3) : "—"}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
              {pcaVariance ? (
                <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
                  <h3 className="mb-2 font-medium">PCA explained variance</h3>
                  <pre className="overflow-auto text-xs">
                    {JSON.stringify(pcaVariance, null, 2)}
                  </pre>
                </div>
              ) : null}
              {varianceDist ? (
                <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
                  <h3 className="mb-2 font-medium">Variance distribution (top features)</h3>
                  <pre className="overflow-auto text-xs">
                    {JSON.stringify(varianceDist, null, 2)}
                  </pre>
                </div>
              ) : null}
              {!corrData && !pcaVariance && !varianceDist ? (
                <p className="text-atlas-muted">No visualizations available yet.</p>
              ) : null}
            </div>
          ) : null}

          {tab === "recommendations" ? (
            <ul className="space-y-2">
              {recommendations.map((rec, idx) => (
                <li
                  key={idx}
                  className="rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3 text-sm text-atlas-muted"
                >
                  {rec.type ? `[${rec.type}] ` : ""}
                  {rec.message ?? JSON.stringify(rec)}
                </li>
              ))}
              {recommendations.length === 0 ? (
                <p className="text-atlas-muted">No recommendations.</p>
              ) : null}
            </ul>
          ) : null}
        </>
      )}
    </section>
  );
}
