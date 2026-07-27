export default function Footer() {
  return (
<footer className="border-t border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950 print:hidden">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-8 md:grid-cols-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500 text-white font-bold">
                T
              </div>
              <span className="font-bold text-slate-900 dark:text-white">
                The Auditor
              </span>
            </div>
            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
              Intelligent Compliance Assessment powered by AI.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Product
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li>Assessments</li>
              <li>Dashboard</li>
              <li>Reports</li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Resources
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li>TISAX Documentation</li>
              <li>VDA ISA Catalogue</li>
              <li>ENX Portal</li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              Contact
            </h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-500 dark:text-slate-400">
              <li>contact@tisaxassist.com</li>
              <li>+216 00 000 000</li>
              <li>Sfax, Tunisia</li>
            </ul>
          </div>
        </div>

        <div className="mt-10 border-t border-slate-200 pt-6 text-center text-xs text-slate-400 dark:border-slate-800">
          © {new Date().getFullYear()} The Auditor. Academic project — not affiliated with ENX Association.
        </div>
      </div>
    </footer>
  );
}