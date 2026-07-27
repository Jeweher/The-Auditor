import { Link } from "react-router-dom";
import TisaxTeacherWidget from "../components/TisaxTeacherWidget";

export default function Home() {
  return (
    <div>
      {/* ===== HERO ===== */}
      <section className="relative overflow-hidden bg-gradient-to-b from-brand-50 to-white dark:from-slate-900 dark:to-slate-900">
        <div className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center gap-10 lg:flex-row lg:justify-between">
          <div className="text-center lg:max-w-3xl lg:text-left">
            <span className="inline-flex items-center gap-2 rounded-full bg-brand-100 px-4 py-1.5 text-sm font-medium text-brand-700 dark:bg-brand-500/10 dark:text-brand-400">
               Powered by Artificial Intelligence
            </span>
            <h1 className="mt-6 text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-7xl">
              Your intelligent <span className="text-brand-500">TISAX</span>
              <br />
              compliance assessor
            </h1>
            <p className="mt-6 text-lg text-slate-600 dark:text-slate-300">
              The Auditor guides you through the VDA ISA self-assessment
              step by step. An AI assistant asks the right questions, analyzes
              your evidence, and estimates your maturity level — just like a
              real auditor would.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link
                to="/register"
                className="rounded-lg bg-brand-500 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-brand-500/25 hover:bg-brand-600"
              >
                Start your assessment
              </Link>
              <a
                href="#about"
                className="rounded-lg border border-slate-300 px-8 py-3.5 text-base font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Learn about TISAX
              </a>
            </div>
          </div>

            <TisaxTeacherWidget />
          </div>
        </div>
      </section>

      {/* ===== WHAT IS TISAX ===== */}
      <section id="about" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="text-3xl font-bold text-slate-900 dark:text-white">
              What is TISAX?
            </h2>
            <p className="mt-4 text-slate-600 dark:text-slate-300">
              TISAX (Trusted Information Security Assessment Exchange) is the
              automotive industry's standard for information security, created
              by the ENX Association on behalf of the German Association of the
              Automotive Industry (VDA).
            </p>
            <p className="mt-4 text-slate-600 dark:text-slate-300">
              It is built on the VDA ISA catalogue — a set of controls covering
              Information Security, Prototype Protection, and Data Protection.
              Suppliers are assessed against maturity levels (ML0–ML5), with
              ML3 as the standard target.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                "Recognized across the automotive supply chain",
                "Based on the VDA ISA control catalogue",
                "Maturity-based scoring (ML0 to ML5)",
                "Assessment levels AL1, AL2, AL3",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-1 text-brand-500">✓</span>
                  <span className="text-slate-700 dark:text-slate-200">{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-8 dark:border-slate-800 dark:bg-slate-800/50">
            <div className="space-y-4">
              {[
                { level: "ML0", label: "Incomplete", desc: "Process not implemented" },
                { level: "ML1", label: "Performed", desc: "Informal, undocumented" },
                { level: "ML2", label: "Managed", desc: "Documented, responsibilities defined" },
                { level: "ML3", label: "Established", desc: "Standard process, consistently applied", target: true },
                { level: "ML4", label: "Predictable", desc: "Measured with KPIs" },
                { level: "ML5", label: "Optimizing", desc: "Continuously improved" },
              ].map((ml) => (
                <div
                  key={ml.level}
                  className={`flex items-center gap-4 rounded-lg p-3 ${
                    ml.target
                      ? "bg-brand-500 text-white"
                      : "bg-white dark:bg-slate-900"
                  }`}
                >
                  <span className={`font-bold ${ml.target ? "text-white" : "text-brand-500"}`}>
                    {ml.level}
                  </span>
                  <div>
                    <div className={`text-sm font-semibold ${ml.target ? "text-white" : "text-slate-900 dark:text-white"}`}>
                      {ml.label} {ml.target && "· Target"}
                    </div>
                    <div className={`text-xs ${ml.target ? "text-brand-50" : "text-slate-500 dark:text-slate-400"}`}>
                      {ml.desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
       </div>
      </section>

      {/* ===== SERVICES ===== */}
      <section className="bg-slate-50 dark:bg-slate-950">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-slate-900 dark:text-white">
              How TISAX Assist helps you
            </h2>
            <p className="mt-4 text-slate-600 dark:text-slate-300">
              An AI-driven workflow from first question to final report.
            </p>
          </div>
          <div className="mt-14 grid gap-8 md:grid-cols-3">
            {[
              {
                icon: "💬",
                title: "Guided AI interview",
                desc: "A conversational assistant asks tailored follow-up questions for each control, grouped intelligently to save your time.",
              },
              {
                icon: "📄",
                title: "Evidence analysis",
                desc: "Upload your policies, procedures or records. The AI verifies your declaration and improves the reliability of your assessment.",
              },
              {
                icon: "📊",
                title: "Maturity & reports",
                desc: "Get a maturity level per control, a compliance dashboard, and actionable recommendations aligned with the VDA ISA Results sheet.",
              },
            ].map((s) => (
              <div
                key={s.title}
                className="rounded-2xl border border-slate-200 bg-white p-8 dark:border-slate-800 dark:bg-slate-900"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-100 text-2xl dark:bg-brand-500/10">
                  {s.icon}
                </div>
                <h3 className="mt-5 text-lg font-semibold text-slate-900 dark:text-white">
                  {s.title}
                </h3>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                  {s.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== DOCUMENTATION DOWNLOAD ===== */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
        <div className="rounded-2xl bg-gradient-to-r from-brand-500 to-brand-700 p-10 text-center sm:p-16">
          <h2 className="text-3xl font-bold text-white">
            Official TISAX documentation
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-brand-50">
            Access the official resources from the ENX Association to understand
            the requirements before or during your assessment.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <a
              href="https://portal.enx.com/en-US/TISAX/downloads/"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg bg-white px-6 py-3 text-sm font-semibold text-brand-700 hover:bg-brand-50"
            >
              📥 VDA ISA Catalogue (ENX)
            </a>
            <a
              href="https://www.enx.com/en-US/tisax/"
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg border border-white/40 px-6 py-3 text-sm font-semibold text-white hover:bg-white/10"
            >
              🌐 Visit ENX Portal
            </a>
          </div>
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section className="border-t border-slate-200 dark:border-slate-800">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white">
            Ready to assess your TISAX compliance?
          </h2>
          <p className="mt-4 text-slate-600 dark:text-slate-300">
            Create an account and let the AI guide your first assessment.
          </p>
          <Link
            to="/register"
            className="mt-8 inline-block rounded-lg bg-brand-500 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-brand-500/25 hover:bg-brand-600"
          >
            Get started for free
          </Link>
        </div>
      </section>
    </div>
  );
}