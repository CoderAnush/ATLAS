"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
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
};

export default function DatasetsPage() {
  const { authFetch } = useAuth();
  const [items, setItems] = useState<Dataset[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("newest");
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const query = useMemo(() => {
    const params = new URLSearchParams({ sort, limit: String(limit), offset: String(offset) });
    if (q.trim()) params.set("q", q.trim());
    return params.toString();
  }, [q, sort, offset]);

  useEffect(() => {
    async function load() {
      const res = await authFetch(`/v1/datasets/search?${query}`);
      if (res.ok) {
        const body = (await res.json()) as { items: Dataset[]; total: number };
        setItems(body.items);
        setTotal(body.total);
      }
    }
    void load();
  }, [authFetch, query]);

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-3xl text-atlas-ink">Dataset browser</h2>
          <p className="mt-2 text-atlas-muted">Search, filter, and open versioned datasets.</p>
        </div>
        <Link href="/datasets/upload" className="rounded-md bg-atlas-accent px-4 py-2 text-white">
          Upload
        </Link>
      </div>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          className="flex-1 rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
          placeholder="Search by name or filename"
          value={q}
          onChange={(e) => {
            setOffset(0);
            setQ(e.target.value);
          }}
        />
        <select
          className="rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
          <option value="largest">Largest</option>
          <option value="smallest">Smallest</option>
          <option value="most_downloaded">Most downloaded</option>
          <option value="most_recent">Most recent</option>
        </select>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((ds) => (
          <Link
            key={ds.id}
            href={`/datasets/${ds.id}`}
            className="rounded-xl border border-atlas-line bg-atlas-panel p-4 transition hover:border-atlas-accent"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium text-atlas-ink">{ds.name}</p>
              <span className="text-xs uppercase text-atlas-muted">{ds.status}</span>
            </div>
            <p className="mt-1 text-sm text-atlas-muted">
              {ds.original_filename} · {ds.format.toUpperCase()} · v{ds.current_version}
            </p>
            {ds.tags?.length ? (
              <p className="mt-2 text-xs text-atlas-muted">{ds.tags.join(", ")}</p>
            ) : null}
          </Link>
        ))}
      </div>
      <div className="flex items-center justify-between text-sm text-atlas-muted">
        <span>
          Showing {items.length} of {total}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-md border border-atlas-line px-3 py-1 disabled:opacity-40"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            Previous
          </button>
          <button
            type="button"
            className="rounded-md border border-atlas-line px-3 py-1 disabled:opacity-40"
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
