"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type TrainingJob = {
  id: string;
  status: string;
  progress: number;
};

type HpoJob = {
  id: string;
  status: string;
  progress: number;
  training_job_id: string;
  best_score: number | null;
  metric_objective: string;
  trials_completed: number;
};

type Study = {
  id: string;
  study_name: string;
  algorithm: string;
  optimizer: string;
  status: string;
  best_score: number | null;
};

export default function HpoIndexPage() {
  const { authFetch } = useAuth();
  const [trainingJobs, setTrainingJobs] = useState<TrainingJob[]>([]);
  const [jobs, setJobs] = useState<HpoJob[]>([]);
  const [studies, setStudies] = useState<Study[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const [trainingRes, jobsRes, studiesRes] = await Promise.all([
      authFetch("/v1/training/jobs"),
      authFetch("/v1/hpo/jobs"),
      authFetch("/v1/hpo/studies"),
    ]);
    if (trainingRes.ok) {
      const all = (await trainingRes.json()) as TrainingJob[];
      setTrainingJobs(all.filter((item) => item.status === "completed"));
    }
    if (jobsRes.ok) setJobs((await jobsRes.json()) as HpoJob[]);
    if (studiesRes.ok) setStudies((await studiesRes.json()) as Study[]);
  }

  useEffect(() => {
    void load();
  }, []);

  async function run(trainingJobId: string) {
    setBusy(trainingJobId);
    setMessage(null);
    const res = await authFetch(`/v1/hpo/run/${trainingJobId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        optimizer: "optuna",
        metric_objective: "accuracy",
        budget: { max_trials: 10, parallel_workers: 1 },
        config: {},
      }),
    });
    setBusy(null);
    if (!res.ok) {
      setMessage((await res.json()).detail || "Failed to start optimization");
      return;
    }
    const body = (await res.json()) as { job_id: string };
    setMessage(`Optimization job ${body.job_id} started.`);
    await load();
  }

  return (
    <section className="mx-auto max-w-6xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Hyperparameter Optimization</h2>
        <p className="mt-2 text-atlas-muted">
          Optimize approved training jobs and review the best trial before final approval.
        </p>
      </div>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}

      <div>
        <h3 className="font-display text-xl text-atlas-ink">Approved training jobs</h3>
        <ul className="mt-3 space-y-2">
          {trainingJobs.map((job) => (
            <li
              key={job.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
            >
              <p className="text-sm">
                {job.id} · {job.status} · {job.progress}%
              </p>
              <button
                type="button"
                disabled={busy === job.id}
                onClick={() => void run(job.id)}
                className="rounded-md bg-atlas-accent px-3 py-2 text-white disabled:opacity-40"
              >
                {busy === job.id ? "Starting…" : "Run HPO"}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="font-display text-xl text-atlas-ink">Optimization jobs</h3>
        <ul className="mt-3 space-y-2">
          {jobs.map((job) => (
            <li
              key={job.id}
              className="flex items-center justify-between rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3"
            >
              <p className="text-sm">
                {job.status} · {job.metric_objective} · trials {job.trials_completed} · best{" "}
                {job.best_score ?? "n/a"}
              </p>
              <Link href={`/hpo/${job.id}`} className="rounded-md border border-atlas-line px-3 py-2 text-sm">
                Open
              </Link>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="font-display text-xl text-atlas-ink">Studies</h3>
        <ul className="mt-3 space-y-2">
          {studies.map((study) => (
            <li key={study.id} className="rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3 text-sm">
              {study.study_name} · {study.algorithm} · {study.optimizer} · {study.status} · best{" "}
              {study.best_score ?? "n/a"}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
