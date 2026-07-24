"use client";

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

type Member = {
  id: string;
  user_id: string;
  role: string;
  email: string | null;
};

export default function MembersPage() {
  const { user, authFetch } = useAuth();
  const [members, setMembers] = useState<Member[]>([]);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("viewer");
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    if (!user?.active_organization_id) return;
    const res = await authFetch(`/v1/organizations/${user.active_organization_id}/members`);
    if (res.ok) setMembers((await res.json()) as Member[]);
  }

  useEffect(() => {
    void load();
  }, [user?.active_organization_id]);

  async function invite(event: FormEvent) {
    event.preventDefault();
    if (!user?.active_organization_id) return;
    const res = await authFetch(`/v1/organizations/${user.active_organization_id}/invite`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    });
    setMessage(res.ok ? "Invitation recorded." : "Invite failed (admin/owner required).");
    if (res.ok) {
      setEmail("");
      await load();
    }
  }

  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Members & roles</h2>
        <p className="mt-2 text-atlas-muted">Organization RBAC: owner, admin, ml_engineer, data_scientist, approver, viewer.</p>
      </div>
      <form onSubmit={invite} className="grid gap-2 rounded-2xl border border-atlas-line bg-atlas-panel p-4 sm:grid-cols-[1fr_auto_auto]">
        <input
          className="rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
          type="email"
          placeholder="invitee@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <select
          className="rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
          value={role}
          onChange={(e) => setRole(e.target.value)}
        >
          {["admin", "ml_engineer", "data_scientist", "approver", "viewer"].map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <button type="submit" className="rounded-md bg-atlas-accent px-3 py-2 text-white">
          Invite
        </button>
      </form>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}
      <ul className="space-y-2">
        {members.map((member) => (
          <li key={member.id} className="rounded-xl border border-atlas-line bg-atlas-panel px-4 py-3">
            <p className="font-medium">{member.email || member.user_id}</p>
            <p className="text-sm text-atlas-muted">{member.role}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
