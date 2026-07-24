"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Dataset = {
  id: string;
  name: string;
  status: string;
  format: string;
  original_filename: string;
  current_version: number;
  download_count: number;
  project_id: string;
  is_favorite: boolean;
  tags: string[];
  description: string;
};

type Version = {
  id: string;
  version: number;
  status: string;
  size_bytes: number;
  checksum_sha256: string;
  row_estimate: number | null;
  column_estimate: number | null;
  created_at: string;
};

export default function DatasetDetailPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { authFetch } = useAuth();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    const d = await authFetch(`/v1/datasets/${datasetId}`);
    if (d.ok) setDataset((await d.json()) as Dataset);
    const v = await authFetch(`/v1/datasets/${datasetId}/versions`);
    if (v.ok) setVersions((await v.json()) as Version[]);
  }

  useEffect(() => {
    void load();
  }, [datasetId]);

  async function download() {
    const res = await authFetch(`/v1/datasets/${datasetId}/download`, { method: "POST" });
    if (!res.ok) {
      setMessage("Download failed");
      return;
    }
    const body = (await res.json()) as { url: string };
    window.open(body.url, "_blank");
    setMessage("Signed download URL opened");
    await load();
  }

  async function toggleFavorite() {
    await authFetch(`/v1/datasets/${datasetId}/favorite`, { method: "POST" });
    await load();
  }

  async function archive() {
    await authFetch(`/v1/datasets/${datasetId}/archive`, { method: "POST" });
    await load();
  }

  async function restore() {
    await authFetch(`/v1/datasets/${datasetId}/restore`, { method: "POST" });
    await load();
  }

  async function remove() {
    if (!window.confirm("Soft-delete this dataset?")) return;
    await authFetch(`/v1/datasets/${datasetId}`, { method: "DELETE" });
    setMessage("Dataset deleted");
    await load();
  }

  if (!dataset) return <p className="text-atlas-muted">Loading dataset…</p>;

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-3xl text-atlas-ink">{dataset.name}</h2>
          <p className="mt-1 text-atlas-muted">
            {dataset.original_filename} · {dataset.format} · {dataset.status}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={download} className="rounded-md bg-atlas-accent px-3 py-2 text-white">
            Download
          </button>
          <button type="button" onClick={toggleFavorite} className="rounded-md border border-atlas-line px-3 py-2">
            {dataset.is_favorite ? "Unfavorite" : "Favorite"}
          </button>
          {dataset.status === "archived" ? (
            <button type="button" onClick={restore} className="rounded-md border border-atlas-line px-3 py-2">
              Restore
            </button>
          ) : (
            <button type="button" onClick={archive} className="rounded-md border border-atlas-line px-3 py-2">
              Archive
            </button>
          )}
          <button type="button" onClick={remove} className="rounded-md border border-red-300 px-3 py-2 text-red-700">
            Delete
          </button>
        </div>
      </div>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}
      <div className="rounded-xl border border-atlas-line bg-atlas-panel p-4 text-sm text-atlas-muted">
        <p>Current version: v{dataset.current_version}</p>
        <p>Downloads: {dataset.download_count}</p>
        <p>Tags: {dataset.tags?.join(", ") || "—"}</p>
        <p>
          Project:{" "}
          <Link className="text-atlas-accent" href={`/projects/${dataset.project_id}`}>
            open
          </Link>
        </p>
        <p>
          <Link className="text-atlas-accent" href={`/datasets/${dataset.id}/versions`}>
            Version history
          </Link>
        </p>
      </div>
      <div>
        <h3 className="font-display text-xl text-atlas-ink">Versions</h3>
        <ul className="mt-3 space-y-2">
          {versions.map((ver) => (
            <li key={ver.id} className="rounded-lg border border-atlas-line bg-atlas-panel px-4 py-3 text-sm">
              <p className="font-medium text-atlas-ink">
                v{ver.version} · {ver.status}
              </p>
              <p className="text-atlas-muted">
                {ver.size_bytes} bytes · rows≈{ver.row_estimate ?? "?"} · cols≈
                {ver.column_estimate ?? "?"}
              </p>
              <p className="truncate text-atlas-muted">sha256:{ver.checksum_sha256}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
