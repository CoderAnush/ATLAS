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
  quality_before: number | null;
  quality_after: number | null;
  output_version: number | null;
  recipe_id: string | null;
  report_id: string | null;
};

type RecipeStep = Record<string, unknown> & {
  order?: number;
  kind?: string;
  column?: string;
  reason?: string;
  expected_impact?: string;
};

type Recipe = {
  id: string;
  version: number;
  recipe_json: { steps?: RecipeStep[] };
  steps?: RecipeStep[];
};

type Report = {
  id: string;
  summary: string;
  report_json: {
    before?: Record<string, number>;
    after?: Record<string, number>;
    improvement?: Record<string, number>;
  };
  graph_json: Record<string, unknown>;
};

type HistoryEvent = {
  job_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export default function PreparationDetailPage() {
  const params = useParams<{ datasetId: string }>();
  const datasetId = params.datasetId;
  const { authFetch } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [history, setHistory] = useState<HistoryEvent[]>([]);
  const [editedSteps, setEditedSteps] = useState<RecipeStep[] | null>(null);
  const [tab, setTab] = useState<"plan" | "recipe" | "quality" | "history">("plan");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const res = await authFetch(`/v1/preparation/${datasetId}`);
    if (!res.ok) {
      setSummary(null);
      return;
    }
    const body = (await res.json()) as Summary;
    setSummary(body);
    if (body.recipe_id) {
      const rr = await authFetch(`/v1/preparation/recipe/${body.recipe_id}`);
      if (rr.ok) {
        const r = (await rr.json()) as Recipe;
        setRecipe(r);
        if (editedSteps === null) {
          setEditedSteps(r.recipe_json?.steps ?? r.steps ?? []);
        }
      }
    }
    if (body.report_id) {
      const rp = await authFetch(`/v1/preparation/report/${body.report_id}`);
      if (rp.ok) setReport((await rp.json()) as Report);
    }
    const hist = await authFetch(`/v1/preparation/${datasetId}/history`);
    if (hist.ok) setHistory((await hist.json()) as HistoryEvent[]);
  }

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), 4000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetId]);

  async function approve() {
    if (!summary) return;
    setBusy(true);
    setMessage(null);
    const res = await authFetch("/v1/preparation/approve", {
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
    setMessage("Approved — cleaned dataset version created");
    setEditedSteps(null);
    await load();
  }

  async function reject() {
    if (!summary) return;
    setBusy(true);
    setMessage(null);
    const res = await authFetch("/v1/preparation/reject", {
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
    const res = await authFetch("/v1/preparation/export", {
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
    setMessage(body.data_url ? `Export ready: ${body.data_url}` : "Recipe exported");
  }

  function removeStep(idx: number) {
    setEditedSteps((prev) => (prev ?? []).filter((_, i) => i !== idx));
  }

  const steps = editedSteps ?? recipe?.recipe_json?.steps ?? [];
  const before = report?.report_json?.before ?? {};
  const after = report?.report_json?.after ?? {};
  const improvement = report?.report_json?.improvement ?? {};

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-atlas-muted">
            <Link href="/preparation">Preparation</Link> / {datasetId}
          </p>
          <h2 className="font-display text-3xl text-atlas-ink">Cleaning plan</h2>
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
        <p className="text-atlas-muted">No cleaning job yet. Start one from the preparation list.</p>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">Status</p>
              <p className="text-lg font-medium">{summary.status}</p>
            </div>
            <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">Quality before</p>
              <p className="text-lg font-medium">{summary.quality_before ?? "—"}</p>
            </div>
            <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">Quality after</p>
              <p className="text-lg font-medium">{summary.quality_after ?? "—"}</p>
            </div>
            <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
              <p className="text-xs uppercase text-atlas-muted">Output version</p>
              <p className="text-lg font-medium">
                {summary.output_version != null ? `v${summary.output_version}` : "—"}
              </p>
            </div>
          </div>

          <p className="text-atlas-muted">{summary.summary}</p>

          <div className="flex flex-wrap gap-2 border-b border-atlas-line pb-2">
            {(
              [
                ["plan", "Plan"],
                ["recipe", "Recipe"],
                ["quality", "Before / After"],
                ["history", "Timeline"],
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

          {tab === "plan" ? (
            <ol className="space-y-2">
              {steps.map((step, idx) => (
                <li
                  key={idx}
                  className="flex items-start justify-between gap-3 rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
                >
                  <div>
                    <p className="font-medium">
                      Step {String(step.order ?? idx + 1)} · {String(step.kind)}
                      {step.column ? ` · ${String(step.column)}` : ""}
                    </p>
                    <p className="text-sm text-atlas-muted">{String(step.reason ?? "")}</p>
                    <p className="text-sm text-atlas-muted">{String(step.expected_impact ?? "")}</p>
                  </div>
                  {summary.status === "awaiting_approval" ? (
                    <button
                      type="button"
                      className="text-sm text-atlas-muted underline"
                      onClick={() => removeStep(idx)}
                    >
                      Remove
                    </button>
                  ) : null}
                </li>
              ))}
              {steps.length === 0 ? (
                <p className="text-atlas-muted">Waiting for plan generation…</p>
              ) : null}
            </ol>
          ) : null}

          {tab === "recipe" ? (
            <pre className="overflow-auto rounded-xl border border-atlas-line bg-atlas-panel p-4 text-xs">
              {JSON.stringify({ version: 1, steps }, null, 2)}
            </pre>
          ) : null}

          {tab === "quality" ? (
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
                <h3 className="mb-2 font-medium">Before</h3>
                <ul className="space-y-1 text-sm text-atlas-muted">
                  <li>Missing %: {String(before.missing_pct ?? "—")}</li>
                  <li>Duplicates %: {String(before.duplicate_pct ?? "—")}</li>
                  <li>Quality: {String(before.quality_overall ?? "—")}</li>
                  <li>Rows: {String(before.rows ?? "—")}</li>
                  <li>Columns: {String(before.columns ?? "—")}</li>
                </ul>
              </div>
              <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
                <h3 className="mb-2 font-medium">After</h3>
                <ul className="space-y-1 text-sm text-atlas-muted">
                  <li>Missing %: {String(after.missing_pct ?? "—")}</li>
                  <li>Duplicates %: {String(after.duplicate_pct ?? "—")}</li>
                  <li>Quality: {String(after.quality_overall ?? "—")}</li>
                  <li>Rows: {String(after.rows ?? "—")}</li>
                  <li>Columns: {String(after.columns ?? "—")}</li>
                </ul>
              </div>
              <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
                <h3 className="mb-2 font-medium">Improvement</h3>
                <ul className="space-y-1 text-sm text-atlas-muted">
                  <li>Δ Missing %: {String(improvement.missing_pct_delta ?? "—")}</li>
                  <li>Δ Duplicates %: {String(improvement.duplicate_pct_delta ?? "—")}</li>
                  <li>Δ Quality: {String(improvement.quality_delta ?? "—")}</li>
                  <li>Δ Rows: {String(improvement.rows_delta ?? "—")}</li>
                  <li>Δ Columns: {String(improvement.columns_delta ?? "—")}</li>
                </ul>
              </div>
            </div>
          ) : null}

          {tab === "history" ? (
            <ol className="space-y-2">
              {history.map((event, idx) => (
                <li
                  key={`${event.job_id}-${idx}`}
                  className="rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
                >
                  <p className="font-medium">{event.event_type}</p>
                  <p className="text-sm text-atlas-muted">{event.created_at}</p>
                  <pre className="mt-2 overflow-auto text-xs">
                    {JSON.stringify(event.payload, null, 2)}
                  </pre>
                </li>
              ))}
              {history.length === 0 ? (
                <p className="text-atlas-muted">No transformation history yet.</p>
              ) : null}
            </ol>
          ) : null}
        </>
      )}
    </section>
  );
}
