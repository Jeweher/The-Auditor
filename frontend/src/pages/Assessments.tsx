import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import * as assessmentsApi from "../api/assessments";
import type { Assessment } from "../types";
import axios from "axios";

const AL_OPTIONS = [
  { value: "AL1", label: "AL1 — Low protection needs" },
  { value: "AL2", label: "AL2 — High protection needs" },
  { value: "AL3", label: "AL3 — Very high protection needs" },
];

const TARGET_OPTIONS = [
  { value: 3, label: "ML3 — Established (standard TISAX target)" },
  { value: 4, label: "ML4 — Predictable (requires measurement evidence)" },
  { value: 5, label: "ML5 — Optimizing (requires improvement evidence)" },
];

const DOMAIN_OPTIONS = [
  { value: "", label: "All domains" },
  { value: "IS", label: "Information Security" },
  { value: "PP", label: "Prototype Protection" },
  { value: "DP", label: "Data Protection" },
];

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    in_progress: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
    completed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400",
  };
  const label: Record<string, string> = {
    in_progress: "In progress",
    completed: "Completed",
  };
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${styles[status] || "bg-slate-100 text-slate-600"}`}>
      {label[status] || status}
    </span>
  );
}

export default function Assessments() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  // Create form state
  const [name, setName] = useState("");
  const [al, setAl] = useState("AL1");
  const [target, setTarget] = useState(3);
  const [domain, setDomain] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  async function loadAssessments() {
    setLoading(true);
    try {
      const data = await assessmentsApi.listAssessments();
      setAssessments(data);
    } catch {
      // Non-fatal: leave the list empty; the empty state below invites creation.
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAssessments();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreateError(null);
    setCreating(true);
    try {
      const created = await assessmentsApi.createAssessment({
        name,
        assessment_level: al,
        target_maturity_level: target,
        domain: domain || null,
      });
      setShowModal(false);
      setName("");
      navigate(`/assessments/${created.id}/chat`);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setCreateError(err.response?.data?.message || err.response?.data?.detail || "Could not create assessment.");
      } else {
        setCreateError("Something went wrong.");
      }
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this assessment? This cannot be undone.")) return;
    await assessmentsApi.deleteAssessment(id);
    setAssessments((prev) => prev.filter((a) => a.id !== id));
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Your assessments
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Track and continue your TISAX self-assessments.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600"
        >
          + New assessment
        </button>
      </div>

      {/* List */}
      {loading ? (
        <div className="mt-10 text-center text-slate-400">Loading...</div>
      ) : assessments.length === 0 ? (
        <div className="mt-16 rounded-2xl border border-dashed border-slate-300 p-16 text-center dark:border-slate-700">
          <p className="text-lg font-medium text-slate-700 dark:text-slate-200">
            No assessments yet
          </p>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            Create your first assessment to start the AI-guided interview.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="mt-6 rounded-lg bg-brand-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-600"
          >
            + New assessment
          </button>
        </div>
      ) : (
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {assessments.map((a) => (
            <div
              key={a.id}
              className="flex flex-col rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-800/50"
            >
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-slate-900 dark:text-white">{a.name}</h3>
                <StatusBadge status={a.status} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">{a.assessment_level}</span>
                <span className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-700">Target ML{a.target_maturity_level}</span>
              </div>

              <div className="mt-4">
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span>Progress</span>
                  <span>{a.progress_percent}%</span>
                </div>
                <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700">
                  <div
                    className="h-full rounded-full bg-brand-500"
                    style={{ width: `${a.progress_percent}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  {a.completed_controls}/{a.total_controls} controls · {a.skipped_controls} skipped
                </p>
              </div>

              <div className="mt-5 flex gap-2">
                <button
                  onClick={() => navigate(`/assessments/${a.id}/chat`)}
                  className="flex-1 rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
                >
                  Continue
                </button>
                <button
                  onClick={() => navigate(`/assessments/${a.id}/dashboard`)}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  Dashboard
                </button>
                <button
                  onClick={() => handleDelete(a.id)}
                  className="rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:border-red-500/30 dark:text-red-400 dark:hover:bg-red-500/10"
                  aria-label="Delete assessment"
                >
                  🗑
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 dark:bg-slate-800">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white">
              New assessment
            </h2>

            {createError && (
              <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Q3 2026 TISAX Assessment"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Assessment Level
                </label>
                <select
                  value={al}
                  onChange={(e) => setAl(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  {AL_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Target maturity level
                </label>
                <select
                  value={target}
                  onChange={(e) => setTarget(Number(e.target.value))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  {TARGET_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Domain
                </label>
                <select
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  {DOMAIN_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}