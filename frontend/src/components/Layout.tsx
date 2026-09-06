import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
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
      { to: "/allotments", label: "Salesman Allotments", permission: "allotment:view" },
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

function findPageLabel(pathname: string): string {
  if (pathname.startsWith("/profile")) return "Profile";
  for (const section of NAV_SECTIONS) {
    for (const item of section.items) {
      if (item.to === "/" ? pathname === "/" : pathname.startsWith(item.to)) {
        return item.label;
      }
    }
  }
  return "Shoe Xpress";
}

export default function Layout() {
  const { user, logout, hasPermission } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#f6f7f9]">
      {/* Backdrop: only rendered (and only intercepts taps) while the mobile drawer is open. */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-40 w-64 shrink-0 bg-[#111827] text-slate-200 flex flex-col transition-transform duration-200 ease-out",
          "md:static md:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="px-5 py-5 border-b border-white/10 flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold tracking-wide text-white">SHOE XPRESS</div>
            <div className="text-xs text-slate-400">Inventory Intelligence</div>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="md:hidden text-slate-400 hover:text-white text-xl leading-none px-2"
            aria-label="Close menu"
          >
            ×
          </button>
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
                    onClick={() => setSidebarOpen(false)}
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
          <NavLink to="/profile" onClick={() => setSidebarOpen(false)} className="block hover:opacity-80">
            <div className="text-sm font-medium text-white truncate">{user?.full_name}</div>
            <div className="text-xs text-slate-400 truncate">{user?.role.name}</div>
          </NavLink>
          <div className="mt-2 flex gap-3 text-xs">
            <NavLink
              to="/profile"
              onClick={() => setSidebarOpen(false)}
              className="text-slate-400 hover:text-white underline underline-offset-2"
            >
              Profile
            </NavLink>
            <button onClick={logout} className="text-slate-400 hover:text-white underline underline-offset-2">
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden flex items-center gap-3 bg-[#111827] text-white px-4 py-3 shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-2xl leading-none px-1 -ml-1"
            aria-label="Open menu"
          >
            ☰
          </button>
          <span className="text-sm font-medium truncate">{findPageLabel(location.pathname)}</span>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-[1400px] mx-auto p-4 md:p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
