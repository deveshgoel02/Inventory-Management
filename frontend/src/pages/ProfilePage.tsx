import { useEffect, useState, type FormEvent } from "react";
import { api, apiErrorMessage } from "../api/client";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { useAuth } from "../state/AuthContext";

interface RoleOption {
  id: number;
  name: string;
}

export default function ProfilePage() {
  const { user, hasPermission, refreshUser } = useAuth();
  const canManageUsers = hasPermission("user:manage");

  // Account details (name/email/role)
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [email, setEmail] = useState(user?.email ?? "");
  const [roleId, setRoleId] = useState<number | "">("");
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);

  // Password change
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name);
      setEmail(user.email);
      setRoleId(user.role.id);
    }
  }, [user]);

  useEffect(() => {
    if (canManageUsers) {
      api.get<RoleOption[]>("/roles").then((r) => setRoles(r.data));
    }
  }, [canManageUsers]);

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setProfileError(null);
    setProfileSuccess(false);
    setSavingProfile(true);
    try {
      // Name/email go through the self-service endpoint; role (admin-only)
      // goes through the same user-management endpoint the Users page uses,
      // which also guards against demoting the last active admin.
      await api.patch("/auth/me", { full_name: fullName, email });
      if (canManageUsers && user && roleId !== user.role.id) {
        await api.patch(`/users/${user.id}`, { role_id: roleId });
      }
      await refreshUser();
      setProfileSuccess(true);
    } catch (err) {
      setProfileError(apiErrorMessage(err));
    } finally {
      setSavingProfile(false);
    }
  };

  const changePassword = async (e: FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirmation don't match.");
      return;
    }

    setChangingPassword(true);
    try {
      await api.post("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(apiErrorMessage(err));
    } finally {
      setChangingPassword(false);
    }
  };

  if (!user) return null;

  return (
    <div>
      <PageHeader title="Profile" description="Your account details and password." />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">Account Details</div>

          {profileSuccess && (
            <div className="mb-3 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-3 py-2">
              Profile updated successfully.
            </div>
          )}
          {profileError && <div className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{profileError}</div>}

          <form onSubmit={saveProfile} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Full Name</label>
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
              {canManageUsers ? (
                <>
                  <select
                    value={roleId}
                    onChange={(e) => setRoleId(Number(e.target.value))}
                    className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm"
                  >
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Changing your own role takes effect immediately. You can't remove the last active admin.
                  </p>
                </>
              ) : (
                <div>
                  <Badge label={user.role.name} />
                  <p className="text-[11px] text-slate-400 mt-1">Only an admin can change roles.</p>
                </div>
              )}
            </div>
            <button
              type="submit"
              disabled={savingProfile}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded"
            >
              {savingProfile ? "Saving…" : "Save Changes"}
            </button>
          </form>

          <div className="mt-4 pt-4 border-t border-slate-100">
            <div className="text-xs text-slate-500 mb-1">Permissions</div>
            <div className="flex flex-wrap gap-1">
              {user.permissions.map((p) => (
                <span key={p} className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                  {p}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">Change Password</div>

          {passwordSuccess && (
            <div className="mb-3 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-3 py-2">
              Password changed successfully.
            </div>
          )}
          {passwordError && <div className="mb-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{passwordError}</div>}

          <form onSubmit={changePassword} className="space-y-3">
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
              disabled={changingPassword}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded"
            >
              {changingPassword ? "Saving…" : "Change Password"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
