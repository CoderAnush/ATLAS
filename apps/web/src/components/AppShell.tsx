"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { clsx } from "clsx";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/datasets", label: "Datasets" },
  { href: "/experiments", label: "Experiments" },
  { href: "/models", label: "Models" },
  { href: "/deployments", label: "Deployments" },
  { href: "/monitoring", label: "Monitoring" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem("atlas-theme");
    const preferDark = stored === "dark";
    setDark(preferDark);
    document.documentElement.classList.toggle("dark", preferDark);
  }, []);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    window.localStorage.setItem("atlas-theme", next ? "dark" : "light");
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
      </aside>
      <div className="flex min-h-screen flex-col">
        <header className="flex items-center justify-between border-b border-atlas-line bg-atlas-panel/70 px-6 py-4 backdrop-blur">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-atlas-muted">Phase 1 foundation</p>
            <h1 className="font-display text-xl text-atlas-ink">Platform shell</h1>
          </div>
          <button
            type="button"
            onClick={toggleTheme}
            className="rounded-md border border-atlas-line px-3 py-2 text-sm text-atlas-ink hover:bg-atlas-bg"
          >
            {dark ? "Light" : "Dark"} theme
          </button>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
