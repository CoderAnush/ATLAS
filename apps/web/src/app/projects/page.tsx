"use client";

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Project = {
  id: string;
  name: string;
  slug: string;
  description: string;
};

export default function ProjectsPage() {
  const { authFetch } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState("");

  async function load() {
    const res = await authFetch("/v1/projects");
    if (res.ok) setProjects((await res.json()) as Project[]);
  }

  useEffect(() => {
    void load();
  }, []);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    const res = await authFetch("/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    if (res.ok) {
      setName("");
      await load();
    }
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Projects</h2>
        <p className="mt-2 text-atlas-muted">
          Lightweight tenant-scoped projects for RBAC. Dataset ingestion arrives in Phase 3.
        </p>
      </div>
      <form onSubmit={createProject} className="flex gap-2">
        <input
          className="flex-1 rounded-md border border-atlas-line bg-atlas-panel px-3 py-2"
          placeholder="New project name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit" className="rounded-md bg-atlas-accent px-3 py-2 text-white">
          Create
        </button>
      </form>
      <ul className="space-y-2">
        {projects.map((project) => (
          <li key={project.id} className="rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3">
            <p className="font-medium">{project.name}</p>
            <p className="text-sm text-atlas-muted">{project.slug}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
