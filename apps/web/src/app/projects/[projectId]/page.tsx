"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Project = {
  id: string;
  name: string;
  slug: string;
  description: string;
};

type Dataset = {
  id: string;
  name: string;
  status: string;
  format: string;
  original_filename: string;
  current_version: number;
  download_count: number;
};

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { authFetch } = useAuth();
  const [project, setProject] = useState<Project | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);

  useEffect(() => {
    async function load() {
      const p = await authFetch(`/v1/projects/${projectId}`);
      if (p.ok) setProject((await p.json()) as Project);
      const d = await authFetch(`/v1/datasets?project_id=${projectId}`);
      if (d.ok) {
        const body = (await d.json()) as { items: Dataset[] };
        setDatasets(body.items);
      }
    }
    void load();
  }, [authFetch, projectId]);

  if (!project) {
    return <p className="text-atlas-muted">Loading project…</p>;
  }

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-3xl text-atlas-ink">{project.name}</h2>
          <p className="mt-1 text-atlas-muted">{project.description || "No description"}</p>
        </div>
        <Link
          href={`/datasets/upload?project_id=${project.id}`}
          className="rounded-md bg-atlas-accent px-4 py-2 text-white"
        >
          Upload dataset
        </Link>
      </div>
      <div className="grid gap-3">
        {datasets.length === 0 ? (
          <p className="text-atlas-muted">No datasets yet.</p>
        ) : (
          datasets.map((ds) => (
            <Link
              key={ds.id}
              href={`/datasets/${ds.id}`}
              className="rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3 hover:border-atlas-accent"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">{ds.name}</p>
                <span className="text-xs uppercase tracking-wide text-atlas-muted">{ds.status}</span>
              </div>
              <p className="text-sm text-atlas-muted">
                {ds.original_filename} · {ds.format} · v{ds.current_version} · {ds.download_count}{" "}
                downloads
              </p>
            </Link>
          ))
        )}
      </div>
    </section>
  );
}
