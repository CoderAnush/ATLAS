"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Project = {
  id: string;
  name: string;
  slug: string;
  description: string;
  tags: string[];
  is_archived: boolean;
};

export default function ProjectsPage() {
  const { authFetch } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const res = await authFetch("/v1/projects");
    if (res.ok) setProjects((await res.json()) as Project[]);
  }

  useEffect(() => {
    void load();
  }, []);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const res = await authFetch("/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    });
    if (!res.ok) {
      setError((await res.json()).detail || "Failed to create project");
      return;
    }
    setName("");
    setDescription("");
    await load();
  }

  return (
    <section className="mx-auto max-w-4xl space-y-8">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Projects</h2>
        <p className="mt-2 text-atlas-muted">
          Organize datasets by project. Each project is tenant-scoped.
        </p>
      </div>
      <form onSubmit={createProject} className="space-y-3 rounded-xl border border-atlas-line bg-atlas-panel p-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            className="flex-1 rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <button type="submit" className="rounded-md bg-atlas-accent px-4 py-2 text-white">
            Create project
          </button>
        </div>
        <textarea
          className="w-full rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
          placeholder="Description (optional)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
        />
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </form>
      <ul className="grid gap-3 sm:grid-cols-2">
        {projects.map((project) => (
          <li key={project.id}>
            <Link
              href={`/projects/${project.id}`}
              className="block rounded-xl border border-atlas-line bg-atlas-panel px-4 py-4 transition hover:border-atlas-accent"
            >
              <p className="font-medium text-atlas-ink">{project.name}</p>
              <p className="text-sm text-atlas-muted">{project.slug}</p>
              {project.description ? (
                <p className="mt-2 line-clamp-2 text-sm text-atlas-muted">{project.description}</p>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
