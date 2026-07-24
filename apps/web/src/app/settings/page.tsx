"use client";

import Link from "next/link";

export default function SettingsPage() {
  return (
    <section className="mx-auto max-w-3xl space-y-4">
      <h2 className="font-display text-3xl text-atlas-ink">Settings</h2>
      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ["/settings/profile", "Profile"],
          ["/settings/api-keys", "API Keys"],
          ["/settings/members", "Members & roles"],
        ].map(([href, label]) => (
          <Link
            key={href}
            href={href}
            className="rounded-xl border border-atlas-line bg-atlas-panel px-4 py-6 text-atlas-ink hover:bg-atlas-bg"
          >
            {label}
          </Link>
        ))}
      </div>
    </section>
  );
}
