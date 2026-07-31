import { useState, type FormEvent } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import * as authApi from "../api/auth";
import axios from "axios";

interface LocationState {
  userId?: string;
  email?: string;
}

export default function VerifyEmail() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LocationState) || {};

  const [userId, setUserId] = useState<string | null>(state.userId || null);
  const [email, setEmail] = useState(state.email || "");
  const [requestEmail, setRequestEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const hasSession = Boolean(userId && email);

  async function handleRequestCode(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await authApi.resendVerification(requestEmail);
      setUserId(user.id);
      setEmail(user.email);
      setInfo("A verification code has been sent to your email.");
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.message || err.response?.data?.detail || "Could not send a code.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    if (!userId) return;
    setError(null);
    setInfo(null);
    setLoading(true);
    try {
      await authApi.verifyEmail(userId, code);
      navigate("/login", { state: { verified: true, email } });
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.message || err.response?.data?.detail || "Verification failed.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!email) return;
    setError(null);
    setInfo(null);
    setResending(true);
    try {
      const user = await authApi.resendVerification(email);
      setUserId(user.id);
      setCode("");
      setInfo("A new code has been sent to your email.");
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.message || err.response?.data?.detail || "Could not resend the code.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-800/50">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Confirm your email</h1>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              {hasSession ? (
                <>
                  We sent a 6-digit code to{" "}
                  <span className="font-medium text-slate-700 dark:text-slate-300">{email}</span>.
                </>
              ) : (
                "Enter your email to receive a verification code."
              )}
            </p>
          </div>

          {info && (
            <div className="mt-6 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
              {info}
            </div>
          )}

          {error && (
            <div className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
              {error}
            </div>
          )}

          {!hasSession ? (
            <form onSubmit={handleRequestCode} className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
                <input
                  type="email"
                  required
                  value={requestEmail}
                  onChange={(e) => setRequestEmail(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  placeholder="you@company.com"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-brand-500 px-4 py-2.5 font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {loading ? "Sending..." : "Send code"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerify} className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Verification code
                </label>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-center text-lg font-semibold tracking-[0.5em] text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  placeholder="000000"
                />
              </div>
              <button
                type="submit"
                disabled={loading || code.length !== 6}
                className="w-full rounded-lg bg-brand-500 px-4 py-2.5 font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {loading ? "Verifying..." : "Verify email"}
              </button>
              <button
                type="button"
                onClick={handleResend}
                disabled={resending}
                className="w-full text-center text-sm font-semibold text-brand-600 hover:text-brand-500 disabled:opacity-50 dark:text-brand-400"
              >
                {resending ? "Sending..." : "Resend code"}
              </button>
            </form>
          )}

          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-500 dark:text-brand-400">
              Back to sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}