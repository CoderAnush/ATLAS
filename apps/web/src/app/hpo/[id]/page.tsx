"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Job = {
  id: string;
  status: string;
  progress: number;
  error_message: string | null;
  best_score: number | null;
  trials_completed: number;
  remaining_trials: number | null;
};

type Study = {
  id: string;
  job_id: string;
  status: string;
  study_name: string;
  algorithm: string;
  optimizer: string;
  best_score: number | null;
  best_params_json: Record<string, unknown>;
};

export default function HpoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { authFetch } = useAuth();
  const [job, setJob] = useState<Job | null>(null);
  const [study, setStudy] = useState<Study | null>(null);
  const [report, setReport] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const jobRes = await authFetch(`/v1/hpo/jobs/${id}`);
    if (jobRes.ok) setJob((await jobRes.json()) as Job);

    const studiesRes = await authFetch("/v1/hpo/studies");
    if (studiesRes.ok) {
      const items = (await studiesRes.json()) as Study[];
      const found = items.find((item) => item.job_id === id) ?? null;
      setStudy(found);
      if (found) {
        const reportRes = await authFetch(`/v1/hpo/report/${found.id}`);
        if (reportRes.ok) setReport(await reportRes.json());
      }
    }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [id]);

  async function approve() {
    if (!study) return;
    const res = await authFetch("/v1/hpo/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ study_id: study.id, note: "Approved from UI" }),
    });
    setMessage(res.ok ? "Study approved." : (await res.json()).detail || "Approve failed");
    await load();
  }

  async function reject() {
    if (!study) return;
    const res = await authFetch("/v1/hpo/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ study_id: study.id, reason: "Rejected from UI" }),
    });
    setMessage(res.ok ? "Study rejected." : (await res.json()).detail || "Reject failed");
    await load();
  }

  return (
    <section className="mx-auto max-w-6xl space-y-6">
      <h2 className="font-display text-3xl text-atlas-ink">HPO job</h2>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}
      <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4 text-sm">
        <p>Status: {job?.status ?? "loading"}</p>
        <p>Progress: {job?.progress ?? 0}%</p>
        <p>Best score: {job?.best_score ?? "n/a"}</p>
        <p>
          Trials: {job?.trials_completed ?? 0} completed / {job?.remaining_trials ?? "n/a"} remaining
        </p>
        {job?.error_message ? <p>Error: {job.error_message}</p> : null}
      </div>

      {study ? (
        <div className="space-y-3 rounded-xl border border-atlas-line bg-atlas-panel p-4">
          <p className="font-medium">{study.study_name}</p>
          <p className="text-sm text-atlas-muted">
            {study.algorithm} · {study.optimizer} · {study.status}
          </p>
          <p className="text-sm text-atlas-muted">Best objective: {study.best_score ?? "n/a"}</p>
          <pre className="overflow-auto rounded-md bg-atlas-bg p-3 text-xs">
            {JSON.stringify(study.best_params_json, null, 2)}
          </pre>
          {study.status === "completed" ? (
            <div className="flex gap-2">
              <button type="button" onClick={() => void approve()} className="rounded-md bg-atlas-accent px-3 py-2 text-white">
                Approve
              </button>
              <button type="button" onClick={() => void reject()} className="rounded-md border border-atlas-line px-3 py-2">
                Reject
              </button>
            </div>
          ) : null}
        </div>
      ) : (
        <p className="text-atlas-muted">Study not generated yet.</p>
      )}

      <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
        <h3 className="mb-2 font-medium">Optimization report</h3>
        <pre className="overflow-auto text-xs">{JSON.stringify(report, null, 2)}</pre>
      </div>
    </section>
  );
}
