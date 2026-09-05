import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../state/AuthContext";
import clsx from "clsx";

const NAV_SECTIONS: { label: string; items: { to: string; label: string; permission?: string }[] }[] = [
  {
    label: "Overview",
    items: [{ to: "/", label: "Executive Dashboard" }],
  },
  {
    label: "Operations",
    items: [
      { to: "/inventory", label: "Inventory", permission: "inventory:view" },
      { to: "/sales", label: "Sales", permission: "sales:view" },
      { to: "/purchasing", label: "Purchasing", permission: "purchase:view" },
      { to: "/aging", label: "Stock Aging", permission: "inventory:view" },
      { to: "/deadlines", label: "Deadlines & Alerts", permission: "inventory:view" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/forecasting", label: "AI Forecasting", permission: "ai:view" },
      { to: "/recommendations", label: "Purchase Recommendations", permission: "ai:view" },
      { to: "/analytics", label: "Analytics & Insights", permission: "ai:view" },
    ],
  },
  {
    label: "Data",
    items: [
      { to: "/imports", label: "Import Center", permission: "import:run" },
      { to: "/reports", label: "Reports", permission: "export:run" },
      { to: "/data-quality", label: "Data Quality", permission: "inventory:view" },
    ],
  },
  {
    label: "Administration",
    items: [
      { to: "/settings", label: "Settings", permission: "settings:manage" },
      { to: "/users", label: "Users & Roles", permission: "user:manage" },
      { to: "/audit-logs", label: "Audit Logs", permission: "audit:view" },
    ],
  },
];

export default function Layout() {
  const { user, logout, hasPermission } = useAuth();

  return (
    <div className="flex h-screen bg-[#f6f7f9]">
      <aside className="w-64 shrink-0 bg-[#111827] text-slate-200 flex flex-col">
        <div className="px-5 py-5 border-b border-white/10">
          <div className="text-sm font-semibold tracking-wide text-white">SHOE XPRESS</div>
          <div className="text-xs text-slate-400">Inventory Intelligence</div>
        </div>
        <nav className="flex-1 overflow-y-auto py-3">
          {NAV_SECTIONS.map((section) => {
            const visibleItems = section.items.filter((i) => !i.permission || hasPermission(i.permission));
            if (visibleItems.length === 0) return null;
            return (
              <div key={section.label} className="mb-4">
                <div className="px-5 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  {section.label}
                </div>
                {visibleItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      clsx(
                        "block px-5 py-2 text-sm rounded-none border-l-2 transition-colors",
                        isActive
                          ? "border-indigo-500 bg-white/5 text-white font-medium"
                          : "border-transparent text-slate-400 hover:text-white hover:bg-white/5"
                      )
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>
        <div className="px-5 py-4 border-t border-white/10">
          <div className="text-sm font-medium text-white truncate">{user?.full_name}</div>
          <div className="text-xs text-slate-400 truncate">{user?.role.name}</div>
          <button
            onClick={logout}
            className="mt-2 text-xs text-slate-400 hover:text-white underline underline-offset-2"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1400px] mx-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
