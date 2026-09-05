import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import type { User } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";

interface RoleOption {
  id: number;
  name: string;
  permissions: string[];
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [roleId, setRoleId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  const loadUsers = () => api.get<User[]>("/users").then((r) => setUsers(r.data));

  useEffect(() => {
    loadUsers();
    api.get<RoleOption[]>("/roles").then((r) => setRoles(r.data));
  }, []);

  const submit = async () => {
    try {
      await api.post("/users", { email, full_name: fullName, password, role_id: roleId });
      setShowForm(false);
      setEmail("");
      setFullName("");
      setPassword("");
      loadUsers();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  const toggleActive = async (u: User) => {
    await api.patch(`/users/${u.id}`, { is_active: !u.is_active });
    loadUsers();
  };

  return (
    <div>
      <PageHeader
        title="Users & Roles"
        description="Role-based access control: ADMIN, MANAGER, INVENTORY_STAFF, VIEWER. Permissions are enforced server-side, not just hidden in the UI."
        actions={
          <button onClick={() => setShowForm(!showForm)} className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-3 py-1.5 rounded">
            {showForm ? "Cancel" : "New User"}
          </button>
        }
      />

      {error && <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      {showForm && (
        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Email</label>
              <input value={email} onChange={(e) => setEmail(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Full Name</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">Role</label>
              <select value={roleId} onChange={(e) => setRoleId(Number(e.target.value))} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full">
                <option value="">Select…</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button onClick={submit} className="mt-3 bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-1.5 rounded">
            Create User
          </button>
        </div>
      )}

      <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
              <th className="py-2 px-3">Name</th>
              <th className="py-2 px-3">Email</th>
              <th className="py-2 px-3">Role</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3"></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-slate-50">
                <td className="py-2 px-3">{u.full_name}</td>
                <td className="py-2 px-3">{u.email}</td>
                <td className="py-2 px-3">{u.role.name}</td>
                <td className="py-2 px-3">
                  <Badge label={u.is_active ? "NORMAL" : "OVERDUE"} />
                </td>
                <td className="py-2 px-3 text-right">
                  <button onClick={() => toggleActive(u)} className="text-xs text-indigo-600 hover:underline">
                    {u.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
