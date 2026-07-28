"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clsx } from "clsx";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/datasets", label: "Datasets" },
  { href: "/datasets/upload", label: "Upload" },
  { href: "/profiling", label: "Profiling" },
  { href: "/preparation", label: "Preparation" },
  { href: "/features", label: "Features" },
  { href: "/training", label: "Training" },
  { href: "/settings", label: "Settings" },
  { href: "/settings/api-keys", label: "API Keys" },
  { href: "/settings/members", label: "Members" },
];

const PUBLIC = new Set(["/login", "/register", "/forgot-password"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, organizations, loading, logout, switchOrganization } = useAuth();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem("atlas-theme");
    const preferDark = stored === "dark";
    setDark(preferDark);
    document.documentElement.classList.toggle("dark", preferDark);
  }, []);

  useEffect(() => {
    if (loading) return;
    const isPublic = PUBLIC.has(pathname);
    if (!user && !isPublic) {
      router.replace("/login");
    }
    if (user && isPublic) {
      router.replace("/");
    }
  }, [user, loading, pathname, router]);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    window.localStorage.setItem("atlas-theme", next ? "dark" : "light");
  }

  if (PUBLIC.has(pathname)) {
    return <main className="min-h-screen">{children}</main>;
  }

  if (loading || !user) {
    return (
      <main className="grid min-h-screen place-items-center text-atlas-muted">
        Loading ATLAS…
      </main>
    );
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[260px_1fr]">
      <aside className="border-b border-atlas-line bg-atlas-panel/90 p-5 backdrop-blur lg:border-b-0 lg:border-r">
        <div className="mb-8">
          <p className="font-display text-3xl font-bold tracking-tight text-atlas-ink">ATLAS</p>
          <p className="mt-1 text-sm text-atlas-muted">AI Engineering Platform</p>
        </div>
        <nav className="flex gap-2 overflow-x-auto lg:flex-col lg:gap-1">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "rounded-md px-3 py-2 text-sm font-medium transition",
                  active
                    ? "bg-atlas-accent text-white"
                    : "text-atlas-muted hover:bg-atlas-bg hover:text-atlas-ink",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-8 space-y-2 border-t border-atlas-line pt-4">
          <label className="text-xs uppercase tracking-wide text-atlas-muted">Organization</label>
          <select
            className="w-full rounded-md border border-atlas-line bg-atlas-bg px-2 py-2 text-sm"
            value={user.active_organization_id || ""}
            onChange={(e) => void switchOrganization(e.target.value)}
          >
            {organizations.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
      </aside>
      <div className="flex min-h-screen flex-col">
        <header className="flex items-center justify-between border-b border-atlas-line bg-atlas-panel/70 px-6 py-4 backdrop-blur">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-atlas-muted">Phase 7 training</p>
            <h1 className="font-display text-xl text-atlas-ink">Signed in as {user.full_name}</h1>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/settings/profile"
              className="rounded-md border border-atlas-line px-3 py-2 text-sm text-atlas-ink hover:bg-atlas-bg"
            >
              Profile
            </Link>
            <button
              type="button"
              onClick={toggleTheme}
              className="rounded-md border border-atlas-line px-3 py-2 text-sm text-atlas-ink hover:bg-atlas-bg"
            >
              {dark ? "Light" : "Dark"} theme
            </button>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-md bg-atlas-accent px-3 py-2 text-sm text-white"
            >
              Log out
            </button>
          </div>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
