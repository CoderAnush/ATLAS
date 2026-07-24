"use client";

import { useAuth } from "@/lib/auth";

export default function DashboardPage() {
  const { user, organizations } = useAuth();
  const active = organizations.find((o) => o.id === user?.active_organization_id);

  return (
    <section className="mx-auto max-w-4xl">
      <div className="rounded-2xl border border-atlas-line bg-atlas-panel/90 p-8 shadow-sm">
        <p className="text-xs uppercase tracking-[0.18em] text-atlas-muted">Authenticated</p>
        <h2 className="mt-2 font-display text-4xl text-atlas-ink">Welcome, {user?.full_name}</h2>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-atlas-muted">
          Phase 2 identity is active. You are working in{" "}
          <strong className="text-atlas-ink">{active?.name || "no organization"}</strong>. Use the
          organization switcher, API keys, and member management from Settings.
        </p>
        <div className="mt-8 grid gap-3 sm:grid-cols-3">
          {["JWT sessions", "RBAC enforced", "Tenant isolated"].map((item) => (
            <div
              key={item}
              className="rounded-xl border border-atlas-line bg-atlas-bg/60 px-4 py-3 text-sm text-atlas-ink"
            >
              {item}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
