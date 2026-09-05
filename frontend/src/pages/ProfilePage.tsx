import { useState, type FormEvent } from "react";
import { api, apiErrorMessage } from "../api/client";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { useAuth } from "../state/AuthContext";

export default function ProfilePage() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!user) return null;

  return (
    <div>
      <PageHeader title="Profile" description="Your account details and password." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">Account</div>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-xs text-slate-500">Full name</dt>
              <dd className="text-slate-800 font-medium">{user.full_name}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Email</dt>
              <dd className="text-slate-800 font-medium">{user.email}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500 mb-1">Role</dt>
              <dd>
                <Badge label={user.role.name} />
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500 mb-1">Permissions</dt>
              <dd className="flex flex-wrap gap-1">
                {user.permissions.map((p) => (
                  <span key={p} className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                    {p}
                  </span>
                ))}
              </dd>
            </div>
          </dl>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">Change Password</div>

          {success && (
            <div className="mb-3 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-3 py-2">
              Password changed successfully.
            </div>
          )}
          {error && <div className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Current Password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">New Password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm"
              />
              <p className="text-[11px] text-slate-400 mt-1">At least 8 characters.</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Confirm New Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded"
            >
              {submitting ? "Saving…" : "Change Password"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
