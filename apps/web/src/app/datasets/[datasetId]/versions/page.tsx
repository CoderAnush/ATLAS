"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Version = {
  id: string;
  version: number;
  status: string;
  size_bytes: number;
  checksum_sha256: string;
  original_filename: string;
  storage_filename: string;
  row_estimate: number | null;
  column_estimate: number | null;
  created_at: string;
};

export default function DatasetVersionsPage() {
  const { datasetId } = useParams<{ datasetId: string }>();
  const { authFetch } = useAuth();
  const [versions, setVersions] = useState<Version[]>([]);

  useEffect(() => {
    async function load() {
      const res = await authFetch(`/v1/datasets/${datasetId}/versions`);
      if (res.ok) setVersions((await res.json()) as Version[]);
    }
    void load();
  }, [authFetch, datasetId]);

  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div>
        <Link href={`/datasets/${datasetId}`} className="text-sm text-atlas-accent">
          ← Dataset
        </Link>
        <h2 className="mt-2 font-display text-3xl text-atlas-ink">Dataset versions</h2>
        <p className="mt-2 text-atlas-muted">Immutable history — uploads never overwrite prior data.</p>
      </div>
      <ol className="space-y-3">
        {versions.map((ver) => (
          <li key={ver.id} className="rounded-xl border border-atlas-line bg-atlas-panel p-4">
            <p className="font-medium text-atlas-ink">
              Version {ver.version} · {ver.status}
            </p>
            <p className="mt-1 text-sm text-atlas-muted">{ver.original_filename}</p>
            <p className="text-sm text-atlas-muted">
              Stored as {ver.storage_filename} · {ver.size_bytes.toLocaleString()} bytes
            </p>
            <p className="text-sm text-atlas-muted">
              Estimates: {ver.row_estimate ?? "?"} rows × {ver.column_estimate ?? "?"} columns
            </p>
            <p className="mt-1 truncate font-mono text-xs text-atlas-muted">{ver.checksum_sha256}</p>
            <p className="mt-1 text-xs text-atlas-muted">{new Date(ver.created_at).toLocaleString()}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
