import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../state/AuthContext";
import { apiErrorMessage } from "../api/client";
import ThemeToggle from "../components/ThemeToggle";

export default function LoginPage() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("admin@shoexpress.co.in");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#111827] px-4 relative">
      <ThemeToggle className="absolute top-4 right-4" />
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="text-white text-lg font-semibold tracking-wide">SHOE XPRESS</div>
          <div className="text-slate-400 dark:text-slate-500 text-sm">Inventory Intelligence</div>
        </div>
        <form onSubmit={onSubmit} className="bg-white dark:bg-slate-800 rounded-lg p-6 shadow-xl">
          <h1 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Sign in</h1>
          {error && (
            <div className="mb-4 text-sm text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800/50 rounded px-3 py-2">
              {error}
            </div>
          )}
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full mb-3 rounded border border-slate-300 dark:border-slate-600 dark:bg-slate-900 dark:text-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full mb-5 rounded border border-slate-300 dark:border-slate-600 dark:bg-slate-900 dark:text-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-medium py-2 rounded transition-colors"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
