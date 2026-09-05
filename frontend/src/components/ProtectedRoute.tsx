import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../state/AuthContext";

export default function ProtectedRoute({ children, permission }: { children: ReactNode; permission?: string }) {
  const { user, loading, hasPermission } = useAuth();

  if (loading) {
    return <div className="flex items-center justify-center h-screen text-slate-400">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (permission && !hasPermission(permission)) {
    return (
      <div className="p-8">
        <div className="bg-white border border-slate-200 rounded-lg p-6 text-center">
          <div className="text-lg font-medium text-slate-800">Access restricted</div>
          <p className="text-sm text-slate-500 mt-1">
            Your role ({user.role.name}) does not have the "{permission}" permission required for this page.
          </p>
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
