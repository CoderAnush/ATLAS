"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Job = {
  id: string;
  status: string;
  progress: number;
  error_message: string | null;
};

type Model = {
  id: string;
  job_id: string;
  name: string;
  algorithm: string;
  problem_type: string;
  status: string;
  summary: string;
  feature_count: number;
  model_size_bytes: number;
  training_seconds: number;
  warnings_json: unknown[];
};

export default function TrainingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { authFetch } = useAuth();
  const [job, setJob] = useState<Job | null>(null);
  const [model, setModel] = useState<Model | null>(null);
  const [report, setReport] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const jobRes = await authFetch(`/v1/training/jobs/${id}`);
    if (jobRes.ok) setJob((await jobRes.json()) as Job);
    const modelsRes = await authFetch("/v1/training/models");
    if (modelsRes.ok) {
      const items = (await modelsRes.json()) as Model[];
      const found = items.find((m) => m.job_id === id) ?? null;
      setModel(found);
      if (found) {
        const rep = await authFetch(`/v1/training/report/${found.id}`);
        if (rep.ok) setReport(await rep.json());
      }
    }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(timer);
  }, [id]);

  async function approve() {
    const res = await authFetch("/v1/training/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: id, note: "Approved from UI" }),
    });
    setMessage(res.ok ? "Model approved." : (await res.json()).detail || "Approve failed");
    await load();
  }

  async function reject() {
    const res = await authFetch("/v1/training/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: id, reason: "Rejected from UI" }),
    });
    setMessage(res.ok ? "Model rejected." : (await res.json()).detail || "Reject failed");
    await load();
  }

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <h2 className="font-display text-3xl text-atlas-ink">Training job</h2>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}
      <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4 text-sm">
        <p>Status: {job?.status ?? "loading"}</p>
        <p>Progress: {job?.progress ?? 0}%</p>
        {job?.error_message ? <p>Error: {job.error_message}</p> : null}
      </div>
      {model ? (
        <div className="space-y-3 rounded-xl border border-atlas-line bg-atlas-panel p-4">
          <p className="font-medium">{model.name}</p>
          <p className="text-sm text-atlas-muted">
            {model.algorithm} · {model.problem_type} · {model.status}
          </p>
          <p className="text-sm text-atlas-muted">
            features {model.feature_count} · size {model.model_size_bytes} bytes ·
            {` ${model.training_seconds.toFixed(2)}s`}
          </p>
          {job?.status === "awaiting_approval" ? (
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
        <p className="text-atlas-muted">Model not generated yet.</p>
      )}
      <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
        <h3 className="mb-2 font-medium">Training report</h3>
        <pre className="overflow-auto text-xs">{JSON.stringify(report, null, 2)}</pre>
      </div>
    </section>
  );
}
