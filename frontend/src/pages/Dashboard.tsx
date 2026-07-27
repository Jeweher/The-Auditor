import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import * as api from "../api/assessments";
import type { Report, ControlRow } from "../types";

const ML_COLORS: Record<string, string> = {
  ml0: "#ef4444",
  ml1: "#f97316",
  ml2: "#f59e0b",
  ml3: "#1fa3a6",
  ml4: "#16828a",
  ml5: "#166970",
  na: "#cbd5e1",
};

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "#10b981",
  medium: "#f59e0b",
  low: "#ef4444",
};

const EVIDENCE_COLORS: Record<string, string> = {
  confirmed: "#10b981",
  measurement_confirmed: "#10b981",
  improvement_confirmed: "#10b981",
  partially_confirmed: "#f59e0b",
  not_required: "#94a3b8",
  missing: "#f97316",
  irrelevant: "#f59e0b",
  contradicted: "#ef4444",
};

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-800/50">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{sub}</p>}
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  const styles: Record<string, string> = {
    completed: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400",
    skipped: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
    not_started: "bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500",
    in_progress: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
    answered: "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[state] || styles.not_started}`}>
      {state.replace("_", " ")}
    </span>
  );
}

function ConfidenceBadge({ level }: { level: string | null }) {
  if (!level) return <span className="text-slate-300">—</span>;
  const color = CONFIDENCE_COLORS[level] || "#94a3b8";
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-semibold text-white"
      style={{ backgroundColor: color }}
    >
      {level}
    </span>
  );
}

export default function Dashboard() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        let targetId = id;
        if (!targetId) {
          const list = await api.listAssessments();
          if (list.length === 0) {
            navigate("/assessments");
            return;
          }
          targetId = list[0].id;
        }
        const r = await api.getReport(targetId);
        setReport(r);
      } catch {
        setError("Could not load the report for this assessment.");
      } finally {
        setLoading(false);
      }
    })();
  }, [id, navigate]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
        Loading dashboard...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center text-rose-500">
        {error || "No report available."}
      </div>
    );
  }

  const { summary } = report;

  const maturityPieData = Object.entries(report.maturity_distribution)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: k.toUpperCase(), value: v, color: ML_COLORS[k] || "#94a3b8" }));

  const confidencePieData = Object.entries(report.confidence_distribution)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: k, value: v, color: CONFIDENCE_COLORS[k] || "#94a3b8" }));

  const evidenceBarData = Object.entries(report.evidence_distribution)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: k.replace(/_/g, " "), value: v, color: EVIDENCE_COLORS[k] || "#94a3b8" }));

  const chapterBarData = report.by_domain.map((row) => ({
    name: `Ch. ${row.key}`,
    maturity: row.average_maturity ?? 0,
    target: row.target,
  }));

  const priorityActions = report.controls
    .filter((c) => c.gap !== null && c.gap > 0 && c.recommendation)
    .sort((a, b) => (b.gap ?? 0) - (a.gap ?? 0))
    .slice(0, 6);

  const visibleControls = showAll ? report.controls : report.controls.filter((c) => c.state !== "not_started");

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{report.name}</h1>
          <div className="mt-1 flex flex-wrap gap-2 text-xs">
            <span className="rounded bg-slate-100 px-2 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {report.assessment_level}
            </span>
            <span className="rounded bg-slate-100 px-2 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              Target ML{report.target_maturity_level}
            </span>
            <span className="rounded bg-slate-100 px-2 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              {report.status.replace("_", " ")}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/assessments/${report.assessment_id}/report`}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            📄 Official report
          </Link>
          <Link
            to={`/assessments/${report.assessment_id}/chat`}
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
          >
            Continue assessment
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Overall Maturity"
          value={summary.overall_maturity !== null ? `ML${summary.overall_maturity}` : "—"}
          sub={`Target: ML${report.target_maturity_level}`}
        />
        <StatCard
          label="Compliance"
          value={`${summary.compliance_percent}%`}
          sub={`${summary.controls_at_target}/${summary.assessed_controls} controls at target`}
        />
        <StatCard
          label="Assessment Completeness"
          value={`${summary.assessment_completeness}%`}
          sub={`${summary.assessed_controls}/${summary.total_controls} controls assessed`}
        />
        <StatCard
          label="Verified vs Declared"
          value={`${summary.verified_percent}%`}
          sub={`${summary.verified_controls} verified · ${summary.declared_controls} declared`}
        />
      </div>

      {/* Charts row */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Maturity donut */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-800/50">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Maturity distribution</h3>
          {maturityPieData.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={maturityPieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>
                  {maturityPieData.map((d, i) => (
                    <Cell key={i} fill={d.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
          <Legend items={maturityPieData} />
        </div>

        {/* Confidence donut */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-800/50">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Confidence</h3>
          {confidencePieData.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={confidencePieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>
                  {confidencePieData.map((d, i) => (
                    <Cell key={i} fill={d.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
          <Legend items={confidencePieData} />
        </div>

        {/* Evidence status */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-800/50">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Evidence status</h3>
          {evidenceBarData.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={evidenceBarData} layout="vertical" margin={{ left: 10 }}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {evidenceBarData.map((d, i) => (
                    <Cell key={i} fill={d.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* By chapter */}
      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-800/50">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          Maturity by chapter <span className="font-normal text-slate-400">(vs target)</span>
        </h3>
        {chapterBarData.length === 0 ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chapterBarData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis domain={[0, 5]} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="maturity" fill="#1fa3a6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="target" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Priority actions */}
      {priorityActions.length > 0 && (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-800/50">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Priority actions</h3>
          <div className="mt-3 space-y-2">
            {priorityActions.map((c) => (
              <div
                key={c.control_number}
                className="flex items-start gap-3 rounded-lg border border-slate-100 p-3 dark:border-slate-700"
              >
                <span className="mt-0.5 rounded bg-rose-100 px-2 py-0.5 text-xs font-bold text-rose-700 dark:bg-rose-500/10 dark:text-rose-400">
                  gap {c.gap}
                </span>
                <div>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    {c.control_number} — {c.title}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{c.recommendation}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Controls table */}
      <div className="mt-6 rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-800/50">
        <div className="flex items-center justify-between p-5 pb-0">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Controls</h3>
          <button
            onClick={() => setShowAll((s) => !s)}
            className="text-xs font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400"
          >
            {showAll ? "Hide not started" : "Show all controls"}
          </button>
        </div>
        <div className="overflow-x-auto p-5">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs uppercase text-slate-400 dark:border-slate-700">
                <th className="py-2 pr-3">Control</th>
                <th className="py-2 pr-3">State</th>
                <th className="py-2 pr-3">ML</th>
                <th className="py-2 pr-3">Gap</th>
                <th className="py-2 pr-3">Confidence</th>
                <th className="py-2 pr-3">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {visibleControls.map((c) => (
                <ControlRowLine
                  key={c.control_number}
                  c={c}
                  expanded={expanded === c.control_number}
                  onToggle={() =>
                    setExpanded((e) => (e === c.control_number ? null : c.control_number))
                  }
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ControlRowLine({
  c,
  expanded,
  onToggle,
}: {
  c: ControlRow;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasDetails = !!(c.finding || c.recommendation);
  return (
    <>
      <tr
        onClick={hasDetails ? onToggle : undefined}
        className={`border-b border-slate-50 dark:border-slate-800 ${hasDetails ? "cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50" : ""}`}
      >
        <td className="py-2.5 pr-3">
          <span className="font-medium text-slate-800 dark:text-slate-100">{c.control_number}</span>
          <span className="ml-2 text-slate-400">{c.title.split("—")[1]?.trim() || c.title}</span>
        </td>
        <td className="py-2.5 pr-3">
          <StateBadge state={c.state} />
        </td>
        <td className="py-2.5 pr-3 text-slate-700 dark:text-slate-200">
          {c.maturity_level !== null ? `ML${c.maturity_level}` : "—"}
        </td>
        <td className="py-2.5 pr-3">
          {c.gap !== null ? (
            <span className={c.gap > 0 ? "font-semibold text-rose-500" : "text-emerald-500"}>{c.gap}</span>
          ) : (
            "—"
          )}
        </td>
        <td className="py-2.5 pr-3">
          <ConfidenceBadge level={c.confidence} />
        </td>
        <td className="py-2.5 pr-3 text-xs text-slate-500 dark:text-slate-400">
          {c.evidence_status?.replace(/_/g, " ") || "—"}
        </td>
      </tr>
      {expanded && hasDetails && (
        <tr className="bg-slate-50 dark:bg-slate-900/50">
          <td colSpan={6} className="px-3 py-3 text-xs">
            {c.finding && (
              <p className="text-slate-600 dark:text-slate-300">
                <span className="font-semibold">Finding:</span> {c.finding}
              </p>
            )}
            {c.recommendation && (
              <p className="mt-1 text-brand-700 dark:text-brand-400">
                <span className="font-semibold">💡</span> {c.recommendation}
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function Legend({ items }: { items: { name: string; value: number; color: string }[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
      {items.map((it) => (
        <div key={it.name} className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: it.color }} />
          {it.name} ({it.value})
        </div>
      ))}
    </div>
  );
}

function EmptyChart() {
  return (
    <div className="flex h-[220px] items-center justify-center text-xs text-slate-300 dark:text-slate-600">
      No data yet
    </div>
  );
}