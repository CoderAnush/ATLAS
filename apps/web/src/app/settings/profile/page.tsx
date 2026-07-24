"use client";

import { FormEvent, useState } from "react";
import { useAuth } from "@/lib/auth";

export default function ProfilePage() {
  const { user, authFetch, refreshMe } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    const res = await authFetch("/v1/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ full_name: fullName }),
    });
    setMessage(res.ok ? "Profile updated." : "Unable to update profile.");
    if (res.ok) await refreshMe();
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    const res = await authFetch("/v1/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
    setMessage(res.ok ? "Password changed." : "Unable to change password.");
    if (res.ok) {
      setCurrentPassword("");
      setNewPassword("");
    }
  }

  return (
    <section className="mx-auto max-w-2xl space-y-8">
      <div>
        <h2 className="font-display text-3xl text-atlas-ink">Profile</h2>
        <p className="mt-2 text-atlas-muted">{user?.email}</p>
      </div>
      <form onSubmit={saveProfile} className="space-y-3 rounded-2xl border border-atlas-line bg-atlas-panel p-6">
        <label className="block text-sm">
          Full name
          <input
            className="mt-1 w-full rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </label>
        <button type="submit" className="rounded-md bg-atlas-accent px-3 py-2 text-white">
          Save profile
        </button>
      </form>
      <form onSubmit={changePassword} className="space-y-3 rounded-2xl border border-atlas-line bg-atlas-panel p-6">
        <h3 className="font-medium text-atlas-ink">Change password</h3>
        <input
          className="w-full rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
          type="password"
          placeholder="Current password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
        />
        <input
          className="w-full rounded-md border border-atlas-line bg-atlas-bg px-3 py-2"
          type="password"
          placeholder="New password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
        <button type="submit" className="rounded-md border border-atlas-line px-3 py-2">
          Update password
        </button>
      </form>
      {message ? <p className="text-sm text-atlas-muted">{message}</p> : null}
    </section>
  );
}
