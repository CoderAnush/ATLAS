"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type FeatureSet = {
  id: string;
  name: string;
  status: string;
  summary: string;
};

type Job = {
  id: string;
  status: string;
  progress: number;
  feature_set_id: string;
  created_at: string;
};

type Model = {
  id: string;
  name: string;
  algorithm: string;
  problem_type: string;
  status: string;
  created_at: string;
};

export default function TrainingIndexPage() {
  const { authFetch } = useAuth();
  const [featureSets, setFeatureSets] = useState<FeatureSet[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [models, setModels] = useState<Model[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const [fsRes, jobsRes, modelsRes] = await Promise.all([
      authFetch("/v1/features"),
      authFetch("/v1/training/jobs"),
      authFetch("/v1/training/models"),
    ]);
    if (fsRes.ok) {
      const all = (await fsRes.json()) as FeatureSet[];
      setFeatureSets(all.filter((x) => x.status === "materialized"));
    }
    if (jobsRes.ok) setJobs((await jobsRes.json()) as Job[]);
    if (modelsRes.ok) setModels((await modelsRes.json()) as Model[]);
  }

  useEffect(() => {
    void load();
  }, []);

  async function run(featureSetId: string) {
    setBusy(featureSetId);
    setMessage(null);
    const res = await authFetch(`/v1/training/run/${featureSetId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ config: {} }),
    });
    setBusy(null);
    if (!res.ok) {
      setMessage((await res.json()).detail || "Failed to start training");
      return;
    }
    const body = (await res.json()) as { job_id: string };
    setMessage(`Training job ${body.job_id} started.`);
    await load();
  }

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Training</h2>
        <p className="mt-2 text-atlas-muted">
          Train models from approved feature matrices. Jobs stop at approval.
        </p>
      </div>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}

      <div>
        <h3 className="font-display text-xl text-atlas-ink">Approved feature sets</h3>
        <ul className="mt-3 space-y-2">
          {featureSets.map((fs) => (
            <li
              key={fs.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
            >
              <div>
                <p className="font-medium">{fs.name}</p>
                <p className="text-sm text-atlas-muted">{fs.summary}</p>
              </div>
              <button
                type="button"
                disabled={busy === fs.id}
                onClick={() => void run(fs.id)}
                className="rounded-md bg-atlas-accent px-3 py-2 text-white disabled:opacity-40"
              >
                {busy === fs.id ? "Starting…" : "Run training"}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="font-display text-xl text-atlas-ink">Training jobs</h3>
        <ul className="mt-3 space-y-2">
          {jobs.map((job) => (
            <li
              key={job.id}
              className="flex items-center justify-between rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
            >
              <p className="text-sm">
                {job.status} · {job.progress}% · {job.id}
              </p>
              <Link href={`/training/${job.id}`} className="rounded-md border border-atlas-line px-3 py-2 text-sm">
                Open
              </Link>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="font-display text-xl text-atlas-ink">Models</h3>
        <ul className="mt-3 space-y-2">
          {models.map((model) => (
            <li key={model.id} className="rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3 text-sm">
              {model.name} · {model.algorithm} · {model.problem_type} · {model.status}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
