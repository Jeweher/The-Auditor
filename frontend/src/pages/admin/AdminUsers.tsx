import { useEffect, useState } from "react";
import * as adminApi from "../../api/admin";
import type { User } from "../../types";

export default function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await adminApi.listUsers();
      setUsers(data);
    } catch {
      setError("Could not load users.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggleActive(user: User) {
    setBusyId(user.id);
    try {
      const updated = await adminApi.updateUserActive(user.id, !user.is_active);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } finally {
      setBusyId(null);
    }
  }

  async function toggleRole(user: User) {
    const nextRole = user.role === "admin" ? "user" : "admin";
    if (!confirm(`${nextRole === "admin" ? "Grant" : "Remove"} admin access for ${user.email}?`)) return;
    setBusyId(user.id);
    try {
      const updated = await adminApi.updateUserRole(user.id, nextRole);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <div className="p-16 text-center text-slate-400">Loading users...</div>;
  if (error) return <div className="p-16 text-center text-rose-500">{error}</div>;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Manage users</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {users.length} account{users.length !== 1 ? "s" : ""}
      </p>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-slate-200 dark:border-slate-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-400">
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Verified</th>
              <th className="px-4 py-3">Joined</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                <td className="px-4 py-3">
                  <p className="font-medium text-slate-800 dark:text-slate-100">{u.full_name}</p>
                  <p className="text-xs text-slate-400">{u.email}</p>
                </td>
                <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                  {u.company_name || "—"}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      u.role === "admin"
                        ? "bg-brand-100 text-brand-700 dark:bg-brand-500/10 dark:text-brand-400"
                        : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                    }`}
                  >
                    {u.role}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      u.is_active
                        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                        : "bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400"
                    }`}
                  >
                    {u.is_active ? "Active" : "Disabled"}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                  {u.email_verified ? "✓" : "—"}
                </td>
                <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                  {new Date(u.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => toggleRole(u)}
                      disabled={busyId === u.id}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
                    >
                      {u.role === "admin" ? "Remove admin" : "Make admin"}
                    </button>
                    <button
                      onClick={() => toggleActive(u)}
                      disabled={busyId === u.id}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40 ${
                        u.is_active ? "bg-rose-500 hover:bg-rose-600" : "bg-emerald-500 hover:bg-emerald-600"
                      }`}
                    >
                      {u.is_active ? "Disable" : "Enable"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}