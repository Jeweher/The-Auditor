import { Fragment, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
} from "recharts";
import * as api from "../api/assessments";
import type { Report as ReportType, ControlRow } from "../types";

function fmt(v: number | null): string {
  return v === null ? "—" : String(v);
}

function resultColor(value: number | null, target: number): string {
  if (value === null) return "text-slate-400";
  if (value >= target) return "text-emerald-600 dark:text-emerald-400 font-semibold";
  if (value >= target - 1) return "text-amber-600 dark:text-amber-400 font-semibold";
  return "text-rose-600 dark:text-rose-400 font-semibold";
}

function StateTag({ state }: { state: string }) {
  const map: Record<string, string> = {
    completed: "text-emerald-600 dark:text-emerald-400",
    skipped: "text-slate-400 italic",
    not_started: "text-slate-300 dark:text-slate-600",
  };
  return <span className={map[state] || "text-slate-500"}>{state.replace("_", " ")}</span>;
}

function EmptyRadar({ label }: { label: string }) {
  return (
    <div className="flex h-[260px] items-center justify-center text-xs text-slate-300 dark:text-slate-600">
      No assessed data yet for {label}
    </div>
  );
}

export default function Report() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ReportType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        setReport(await api.getReport(id));
      } catch {
        setError("Could not load the report.");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  if (loading) return <div className="p-16 text-center text-slate-400">Loading report...</div>;
  if (error || !report)
    return <div className="p-16 text-center text-rose-500">{error || "No report available."}</div>;

  const { summary } = report;
  const company = typeof window !== "undefined" ? localStorage.getItem("user_company_name") : null;

  const controlsFor = (subKey: string): ControlRow[] =>
    report.controls.filter((c) => {
      const p = c.control_number.split(".");
      return `${p[0]}.${p[1]}` === subKey;
    });
  const subchaptersFor = (chapterKey: string) =>
    report.by_subchapter.filter((s) => s.key.split(".")[0] === chapterKey);

  const chapterRadarData = report.by_domain.map((d) => ({
    name: `Ch.${d.key}`,
    result: d.average_maturity ?? 0,
    target: d.target,
  }));
  const subchapterRadarData = report.by_subchapter.map((s) => ({
    name: s.key,
    result: s.average_maturity ?? 0,
    target: s.target,
  }));

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 print:max-w-none print:px-0">
      {/* Toolbar (hidden on print) */}
      <div className="flex items-center justify-between print:hidden">
        <Link
          to={`/assessments/${id}/dashboard`}
          className="text-sm font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400"
        >
          ← Back to dashboard
        </Link>
        <button
          onClick={() => window.print()}
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-600"
        >
          🖨 Print / Save as PDF
        </button>
      </div>

      {/* Report header */}
      <div className="mt-6 overflow-hidden rounded-t-lg border border-slate-200 dark:border-slate-800 print:border-black">
        <div className="h-1.5 bg-gradient-to-r from-brand-500 to-brand-700" />
        <div className="flex items-start justify-between p-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-brand-500">
              VDA ISA / TISAX Self-Assessment Results
            </p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900 dark:text-white print:text-black">
              {report.name}
            </h1>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-500 text-sm font-bold text-white">
            T
          </div>
        </div>
        <table className="w-full border-t border-slate-200 text-sm dark:border-slate-800 print:border-black">
          <tbody>
            <tr className="border-b border-slate-100 dark:border-slate-800 print:border-slate-300">
              <td className="w-1/4 bg-slate-50 px-4 py-2 font-medium text-slate-500 dark:bg-slate-800/50 dark:text-slate-400 print:bg-slate-100 print:text-black">
                Company
              </td>
              <td className="px-4 py-2 text-slate-800 dark:text-slate-100 print:text-black">
                {company || "—"}
              </td>
              <td className="w-1/4 bg-slate-50 px-4 py-2 font-medium text-slate-500 dark:bg-slate-800/50 dark:text-slate-400 print:bg-slate-100 print:text-black">
                Assessment Level
              </td>
              <td className="px-4 py-2 text-slate-800 dark:text-slate-100 print:text-black">
                {report.assessment_level}
              </td>
            </tr>
            <tr className="border-b border-slate-100 dark:border-slate-800 print:border-slate-300">
              <td className="bg-slate-50 px-4 py-2 font-medium text-slate-500 dark:bg-slate-800/50 dark:text-slate-400 print:bg-slate-100 print:text-black">
                Date
              </td>
              <td className="px-4 py-2 text-slate-800 dark:text-slate-100 print:text-black">
                {new Date().toLocaleDateString()}
              </td>
              <td className="bg-slate-50 px-4 py-2 font-medium text-slate-500 dark:bg-slate-800/50 dark:text-slate-400 print:bg-slate-100 print:text-black">
                Status
              </td>
              <td className="px-4 py-2 text-slate-800 dark:text-slate-100 print:text-black">
                {report.status.replace("_", " ")}
              </td>
            </tr>
            <tr>
              <td className="bg-slate-50 px-4 py-2 font-medium text-slate-500 dark:bg-slate-800/50 dark:text-slate-400 print:bg-slate-100 print:text-black">
                Target Maturity Level
              </td>
              <td className="px-4 py-2 font-semibold text-brand-600 dark:text-brand-400 print:text-black">
                ML{report.target_maturity_level}
              </td>
              <td className="bg-slate-50 px-4 py-2 font-medium text-slate-500 dark:bg-slate-800/50 dark:text-slate-400 print:bg-slate-100 print:text-black">
                Result with cutback
              </td>
              <td
                className={`px-4 py-2 text-base font-bold print:text-black ${resultColor(
                  summary.overall_maturity,
                  report.target_maturity_level
                )}`}
              >
                {summary.overall_maturity !== null ? `ML${summary.overall_maturity}` : "—"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Radar: per chapter */}
      <div className="mt-6 rounded-lg border border-slate-200 p-5 dark:border-slate-800 print:border-black">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          Result per chapter <span className="font-normal text-slate-400">(without cutback)</span>
        </h2>
        {chapterRadarData.length === 0 ? (
          <EmptyRadar label="chapters" />
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={chapterRadarData} outerRadius="75%">
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis dataKey="name" tick={{ fontSize: 11 }} />
              <PolarRadiusAxis domain={[0, 5]} tick={{ fontSize: 10 }} angle={30} />
              <Radar
                name="Target"
                dataKey="target"
                stroke="#94a3b8"
                fill="#94a3b8"
                fillOpacity={0.05}
                strokeDasharray="4 3"
              />
              <Radar name="Result" dataKey="result" stroke="#1fa3a6" fill="#1fa3a6" fillOpacity={0.35} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Radar: per subchapter */}
      <div className="mt-6 rounded-lg border border-slate-200 p-5 dark:border-slate-800 print:border-black">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
          Result per subchapter <span className="font-normal text-slate-400">(without cutback)</span>
        </h2>
        {subchapterRadarData.length === 0 ? (
          <EmptyRadar label="subchapters" />
        ) : (
          <ResponsiveContainer width="100%" height={420}>
            <RadarChart data={subchapterRadarData} outerRadius="78%">
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis dataKey="name" tick={{ fontSize: 9 }} />
              <PolarRadiusAxis domain={[0, 5]} tick={{ fontSize: 9 }} angle={20} />
              <Radar
                name="Target"
                dataKey="target"
                stroke="#94a3b8"
                fill="#94a3b8"
                fillOpacity={0.05}
                strokeDasharray="4 3"
              />
              <Radar name="Result" dataKey="result" stroke="#1fa3a6" fill="#1fa3a6" fillOpacity={0.35} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Hierarchical results table */}
      <div className="mt-8 overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b-2 border-brand-500 bg-brand-50 text-left text-xs uppercase text-slate-500 dark:border-brand-500/50 dark:bg-brand-500/10 dark:text-slate-300 print:border-black print:bg-slate-100 print:text-black">
              <th className="py-2 pl-2 pr-2">Chapter / Control</th>
              <th className="py-2 pr-2">State</th>
              <th className="py-2 pr-2">Target</th>
              <th className="py-2 pr-2">Result</th>
              <th className="py-2 pr-2">Cutback</th>
              <th className="py-2 pr-2">Gap</th>
              <th className="py-2">Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {report.by_domain.map((chapter) => (
              <Fragment key={`ch-${chapter.key}`}>
                <tr className="border-b border-slate-200 bg-slate-50 font-semibold dark:border-slate-800 dark:bg-slate-800/50 print:border-black print:bg-slate-50">
                  <td className="py-2 pl-2 pr-2 text-slate-800 dark:text-white print:text-black">
                    Chapter {chapter.key}
                  </td>
                  <td className="py-2 pr-2 text-xs text-slate-400">{chapter.assessed_controls} assessed</td>
                  <td className="py-2 pr-2 print:text-black">ML{chapter.target}</td>
                  <td className={`py-2 pr-2 print:text-black ${resultColor(chapter.average_maturity, chapter.target)}`}>
                    {fmt(chapter.average_maturity)}
                  </td>
                  <td className="py-2 pr-2 print:text-black">{fmt(chapter.average_maturity)}</td>
                  <td className="py-2 pr-2 print:text-black">{fmt(chapter.gap)}</td>
                  <td className="py-2"></td>
                </tr>

                {subchaptersFor(chapter.key).map((sub) => (
                  <Fragment key={`sub-${sub.key}`}>
                    <tr className="border-b border-slate-100 dark:border-slate-800 print:border-slate-300">
                      <td className="py-1.5 pl-6 pr-2 font-medium text-slate-600 dark:text-slate-300 print:text-black">
                        {sub.key}
                      </td>
                      <td className="py-1.5 pr-2 text-xs text-slate-400">{sub.assessed_controls} assessed</td>
                      <td className="py-1.5 pr-2 print:text-black">ML{sub.target}</td>
                      <td className={`py-1.5 pr-2 print:text-black ${resultColor(sub.average_maturity, sub.target)}`}>
                        {fmt(sub.average_maturity)}
                      </td>
                      <td className="py-1.5 pr-2 print:text-black">{fmt(sub.average_maturity)}</td>
                      <td className="py-1.5 pr-2 print:text-black">{fmt(sub.gap)}</td>
                      <td className="py-1.5"></td>
                    </tr>

                    {controlsFor(sub.key).map((c) => (
                      <tr key={c.control_number} className="border-b border-slate-50 dark:border-slate-800/50 print:border-slate-200">
                        <td className="py-1.5 pl-10 pr-2 text-slate-700 dark:text-slate-200 print:text-black">
                          <span className="font-medium">{c.control_number}</span>{" "}
                          <span className="text-slate-400">{c.title.split("—")[1]?.trim() || ""}</span>
                        </td>
                        <td className="py-1.5 pr-2 text-xs">
                          <StateTag state={c.state} />
                        </td>
                        <td className="py-1.5 pr-2 print:text-black">
                          {c.target_level !== null ? `ML${c.target_level}` : "—"}
                        </td>
                        <td
                          className={`py-1.5 pr-2 print:text-black ${
                            c.maturity_level !== null ? resultColor(c.maturity_level, c.target_level ?? report.target_maturity_level) : "text-slate-300"
                          }`}
                        >
                          {c.maturity_level !== null ? `ML${c.maturity_level}` : "—"}
                        </td>
                        <td className="py-1.5 pr-2 print:text-black">
                          {c.cutback_level !== null ? `ML${c.cutback_level}` : "—"}
                        </td>
                        <td className="py-1.5 pr-2 print:text-black">
                          {c.gap !== null ? (
                            <span className={c.gap > 0 ? "font-semibold text-rose-500" : "text-emerald-500"}>
                              {c.gap}
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="py-1.5 text-xs text-slate-500 dark:text-slate-400 print:text-black">
                          {c.recommendation || "—"}
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </Fragment>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-brand-500 bg-brand-50 font-bold dark:border-brand-500/50 dark:bg-brand-500/10 print:border-black print:bg-slate-100">
              <td className="py-2 pl-2 pr-2 text-slate-900 dark:text-white print:text-black">Overall</td>
              <td className="py-2 pr-2 text-xs text-slate-400">
                {summary.assessed_controls}/{summary.total_controls} assessed
              </td>
              <td className="py-2 pr-2 print:text-black">ML{report.target_maturity_level}</td>
              <td className={`py-2 pr-2 print:text-black ${resultColor(summary.overall_maturity, report.target_maturity_level)}`}>
                {summary.overall_maturity !== null ? `ML${summary.overall_maturity}` : "—"}
              </td>
              <td className="py-2 pr-2 print:text-black">
                {summary.overall_maturity !== null ? `ML${summary.overall_maturity}` : "—"}
              </td>
              <td className="py-2 pr-2 print:text-black">
                {summary.overall_maturity !== null
                  ? Math.max(0, report.target_maturity_level - summary.overall_maturity)
                  : "—"}
              </td>
              <td className="py-2"></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <p className="mt-6 text-center text-[10px] text-slate-300 print:text-black">
        Generated by TISAX Assist Compliance — Academic project, not affiliated with ENX Association.
      </p>
    </div>
  );
}