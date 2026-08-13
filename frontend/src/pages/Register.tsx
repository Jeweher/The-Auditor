import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as authApi from "../api/auth";
import axios from "axios";

const SECTORS = [
  "Automotive Supplier",
  "OEM / Vehicle Manufacturer",
  "IT Service Provider",
  "Engineering Services",
  "Logistics",
  "Other",
];

const JOB_TITLES = [
  "CEO / Founder",
  "CISO / Information Security Officer",
  "Compliance Manager",
  "Quality Manager",
  "IT Manager / IT Director",
  "Project Manager",
  "Consultant",
  "Other",
];

const COMPANY_SIZES = [
  "1-10 employees",
  "11-50 employees",
  "51-200 employees",
  "201-1000 employees",
  "1000+ employees",
];

const AUDIT_REASONS = [
  "An existing customer requires it",
  "To become an approved supplier / attract new customers",
  "Required for a specific project or tender I'm participating in",
  "Internal decision — proactively improving our security posture",
  "Other",
];

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Register() {
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [sector, setSector] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [auditReason, setAuditReason] = useState("");

  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function markTouched(field: string) {
    setTouched((t) => ({ ...t, [field]: true }));
  }

  const fullNameError = fullName.trim().length === 0 ? "Full name is required." : null;
  const emailError =
    email.length === 0
      ? "Email is required."
      : !EMAIL_REGEX.test(email)
      ? "Please enter a valid email address."
      : null;
  const passwordError =
    password.length === 0
      ? "Password is required."
      : password.length < 8
      ? "Password must be at least 8 characters."
      : null;
  const confirmPasswordError =
    confirmPassword.length === 0
      ? "Please confirm your password."
      : confirmPassword !== password
      ? "Passwords do not match."
      : null;

  const isValid = !fullNameError && !emailError && !passwordError && !confirmPasswordError;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched({ fullName: true, email: true, password: true, confirmPassword: true });
    setError(null);

    if (!isValid) return;

    setLoading(true);
    try {
      const user = await authApi.register({
        email,
        password,
        full_name: fullName,
        company_name: companyName || undefined,
        sector: sector || undefined,
        job_title: jobTitle || undefined,
        company_size: companySize || undefined,
        audit_reason: auditReason || undefined,
      });
      navigate("/verify-email", { state: { userId: user.id, email: user.email } });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.message || err.response?.data?.detail || "Registration failed.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-800/50">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Create your account</h1>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Start your TISAX self-assessment with AI guidance
            </p>
          </div>

          {error && (
            <div className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Full name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                onBlur={() => markTouched("fullName")}
                className={`mt-1 w-full rounded-lg border px-4 py-2.5 text-slate-900 outline-none focus:ring-2 dark:bg-slate-900 dark:text-white ${
                  touched.fullName && fullNameError
                    ? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
                    : "border-slate-300 focus:border-brand-500 focus:ring-brand-500/20 dark:border-slate-700"
                }`}
                placeholder="Jane Doe"
              />
              {touched.fullName && fullNameError && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{fullNameError}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => markTouched("email")}
                className={`mt-1 w-full rounded-lg border px-4 py-2.5 text-slate-900 outline-none focus:ring-2 dark:bg-slate-900 dark:text-white ${
                  touched.email && emailError
                    ? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
                    : "border-slate-300 focus:border-brand-500 focus:ring-brand-500/20 dark:border-slate-700"
                }`}
                placeholder="you@company.com"
              />
              {touched.email && emailError && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{emailError}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() => markTouched("password")}
                className={`mt-1 w-full rounded-lg border px-4 py-2.5 text-slate-900 outline-none focus:ring-2 dark:bg-slate-900 dark:text-white ${
                  touched.password && passwordError
                    ? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
                    : "border-slate-300 focus:border-brand-500 focus:ring-brand-500/20 dark:border-slate-700"
                }`}
                placeholder="At least 8 characters"
              />
              {touched.password && passwordError && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{passwordError}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Confirm password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onBlur={() => markTouched("confirmPassword")}
                className={`mt-1 w-full rounded-lg border px-4 py-2.5 text-slate-900 outline-none focus:ring-2 dark:bg-slate-900 dark:text-white ${
                  touched.confirmPassword && confirmPasswordError
                    ? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
                    : "border-slate-300 focus:border-brand-500 focus:ring-brand-500/20 dark:border-slate-700"
                }`}
                placeholder="Re-enter your password"
              />
              {touched.confirmPassword && confirmPasswordError && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{confirmPasswordError}</p>
              )}
            </div>

            <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                Company information (optional)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Company name
              </label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                placeholder="Acme Automotive"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Sector</label>
              <select
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="">Select a sector...</option>
                {SECTORS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Job title
              </label>
              <select
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="">Select your job title...</option>
                {JOB_TITLES.map((j) => (
                  <option key={j} value={j}>
                    {j}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Company size
              </label>
              <select
                value={companySize}
                onChange={(e) => setCompanySize(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="">Select company size...</option>
                {COMPANY_SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Why are you starting a TISAX assessment?
              </label>
              <select
                value={auditReason}
                onChange={(e) => setAuditReason(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
              >
                <option value="">Select a reason...</option>
                {AUDIT_REASONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-brand-500 px-4 py-2.5 font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {loading ? "Creating account..." : "Create account"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Already have an account?{" "}
            <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-500 dark:text-brand-400">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}