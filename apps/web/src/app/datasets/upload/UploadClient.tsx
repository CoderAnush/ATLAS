"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";

type Project = { id: string; name: string };

type QueueItem = {
  id: string;
  file: File;
  progress: number;
  status: "queued" | "uploading" | "done" | "error";
  message?: string;
  datasetId?: string;
};

export default function UploadDatasetPage() {
  const { authFetch, accessToken } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState(params.get("project_id") || "");
  const [name, setName] = useState("");
  const [tags, setTags] = useState("");
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    async function load() {
      const res = await authFetch("/v1/projects");
      if (res.ok) {
        const rows = (await res.json()) as Project[];
        setProjects(rows);
        if (!projectId && rows[0]) setProjectId(rows[0].id);
      }
    }
    void load();
  }, [authFetch, projectId]);

  const canUpload = useMemo(() => Boolean(projectId && queue.length), [projectId, queue.length]);

  function enqueue(files: FileList | File[]) {
    const next = Array.from(files).map((file) => ({
      id: `${file.name}-${file.size}-${Math.random()}`,
      file,
      progress: 0,
      status: "queued" as const,
    }));
    setQueue((prev) => [...prev, ...next]);
  }

  async function uploadOne(item: QueueItem) {
    setQueue((prev) =>
      prev.map((q) => (q.id === item.id ? { ...q, status: "uploading", progress: 5 } : q)),
    );
    const form = new FormData();
    form.append("file", item.file);
    form.append("project_id", projectId);
    if (name.trim()) form.append("name", name.trim());
    if (tags.trim()) form.append("tags", tags.trim());

    return new Promise<void>((resolve) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${api}/v1/datasets/upload`);
      if (accessToken) xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);
      xhr.upload.onprogress = (event) => {
        if (!event.lengthComputable) return;
        const pct = Math.round((event.loaded / event.total) * 100);
        setQueue((prev) => prev.map((q) => (q.id === item.id ? { ...q, progress: pct } : q)));
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const body = JSON.parse(xhr.responseText) as { id: string };
          setQueue((prev) =>
            prev.map((q) =>
              q.id === item.id
                ? { ...q, status: "done", progress: 100, datasetId: body.id }
                : q,
            ),
          );
        } else {
          let message = "Upload failed";
          try {
            message = (JSON.parse(xhr.responseText) as { detail?: string }).detail || message;
          } catch {
            /* ignore */
          }
          setQueue((prev) =>
            prev.map((q) => (q.id === item.id ? { ...q, status: "error", message } : q)),
          );
        }
        resolve();
      };
      xhr.onerror = () => {
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id ? { ...q, status: "error", message: "Network error" } : q,
          ),
        );
        resolve();
      };
      xhr.send(form);
    });
  }

  async function startUpload(event: FormEvent) {
    event.preventDefault();
    if (!canUpload) return;
    for (const item of queue.filter((q) => q.status === "queued" || q.status === "error")) {
      await uploadOne(item);
    }
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Upload dataset</h2>
        <p className="mt-2 text-atlas-muted">
          CSV, TSV, Excel, JSON, Parquet, or ZIP. Streaming upload with progress.
        </p>
      </div>
      <form onSubmit={startUpload} className="space-y-4">
        <label className="block text-sm text-atlas-muted">
          Project
          <select
            className="mt-1 w-full rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            required
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <input
          className="w-full rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
          placeholder="Dataset name (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="w-full rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
          placeholder="Tags (comma-separated)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
        <div
          className={`rounded-xl border-2 border-dashed px-6 py-12 text-center transition ${
            dragOver ? "border-atlas-accent bg-atlas-accent/5" : "border-atlas-line bg-atlas-panel"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (e.dataTransfer.files?.length) enqueue(e.dataTransfer.files);
          }}
        >
          <p className="text-atlas-ink">Drag and drop files here</p>
          <p className="mt-1 text-sm text-atlas-muted">or choose from disk</p>
          <input
            className="mt-4 block w-full text-sm"
            type="file"
            multiple
            accept=".csv,.tsv,.xlsx,.json,.parquet,.zip"
            onChange={(e) => e.target.files && enqueue(e.target.files)}
          />
        </div>
        <ul className="space-y-2">
          {queue.map((item) => (
            <li key={item.id} className="rounded-lg border border-atlas-line bg-atlas-panel p-3">
              <div className="flex justify-between gap-2 text-sm">
                <span>{item.file.name}</span>
                <span className="text-atlas-muted">{item.status}</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded bg-atlas-bg">
                <div className="h-full bg-atlas-accent" style={{ width: `${item.progress}%` }} />
              </div>
              {item.message ? <p className="mt-1 text-sm text-red-600">{item.message}</p> : null}
              {item.datasetId ? (
                <button
                  type="button"
                  className="mt-2 text-sm text-atlas-accent"
                  onClick={() => router.push(`/datasets/${item.datasetId}`)}
                >
                  Open dataset
                </button>
              ) : null}
            </li>
          ))}
        </ul>
        <button
          type="submit"
          disabled={!canUpload}
          className="rounded-md bg-atlas-accent px-4 py-2 text-white disabled:opacity-40"
        >
          Start upload
        </button>
      </form>
    </section>
  );
}
