import { useState, type FormEvent } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import * as authApi from "../api/auth";
import axios from "axios";

interface LocationState {
  verified?: boolean;
  email?: string;
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LocationState) || {};

  const [email, setEmail] = useState(state.email || "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNeedsVerification(false);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/assessments");
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const message =
          err.response?.data?.message || err.response?.data?.detail || "Invalid email or password.";
        setError(message);
        if (err.response?.status === 401 && message.toLowerCase().includes("verify")) {
          setNeedsVerification(true);
        }
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setError(null);
    setResending(true);
    try {
      const user = await authApi.resendVerification(email);
      navigate("/verify-email", { state: { userId: user.id, email: user.email } });
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
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Welcome back</h1>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Sign in to continue your assessment
            </p>
          </div>

          {state.verified && !error && (
            <div className="mt-6 rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
              Your email has been verified. You can now sign in.
            </div>
          )}

          {error && (
            <div className="mt-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">
              <p>{error}</p>
              {needsVerification && (
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={resending}
                  className="mt-2 font-semibold text-red-800 underline hover:text-red-900 disabled:opacity-50 dark:text-red-300"
                >
                  {resending ? "Sending code..." : "Resend verification code"}
                </button>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                placeholder="you@company.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-4 py-2.5 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-brand-500 px-4 py-2.5 font-semibold text-white hover:bg-brand-600 disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
            Don't have an account?{" "}
            <Link to="/register" className="font-semibold text-brand-600 hover:text-brand-500 dark:text-brand-400">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}