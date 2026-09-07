import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api } from "../api/client";
import type { AgingBucketRow, Alert, DashboardSummary, StockDeadline } from "../api/types";
import PageHeader from "../components/PageHeader";
import StatCard from "../components/StatCard";
import Badge from "../components/Badge";
import { formatCurrency, formatDateTime, formatNumber } from "../lib/format";
import { useTheme } from "../state/ThemeContext";

export default function DashboardPage() {
  const { theme } = useTheme();
  const axisTick = { fontSize: 11, fill: theme === "dark" ? "#94a3b8" : "#334155" };
  const gridStroke = theme === "dark" ? "#334155" : "#eef0f3";
  const tooltipStyle =
    theme === "dark"
      ? { contentStyle: { background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0" }, labelStyle: { color: "#e2e8f0" } }
      : {};
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [aging, setAging] = useState<AgingBucketRow[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [deadlines, setDeadlines] = useState<StockDeadline[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<DashboardSummary>("/dashboard/summary"),
      api.get<AgingBucketRow[]>("/inventory/aging/summary"),
      api.get<Alert[]>("/alerts?status=OPEN"),
      api.get<StockDeadline[]>("/deadlines"),
    ])
      .then(([s, a, al, d]) => {
        setSummary(s.data);
        setAging(a.data);
        setAlerts(al.data.slice(0, 6));
        setDeadlines(d.data.filter((x) => x.status !== "NORMAL" && x.status !== "RESOLVED").slice(0, 6));
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading || !summary) {
    return <div className="text-slate-400 dark:text-slate-500 text-sm">Loading dashboard…</div>;
  }

  return (
    <div>
      <PageHeader title="Executive Dashboard" description="Live snapshot of stock, sales, and risk across Shoe Xpress." />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total SKUs" value={formatNumber(summary.total_skus)} />
        <StatCard label="Units in Stock" value={formatNumber(summary.total_units_in_stock)} />
        <StatCard label="Inventory Cost Value" value={formatCurrency(summary.total_inventory_cost_value)} />
        <StatCard label="Inventory Selling Value" value={formatCurrency(summary.total_inventory_selling_value)} />
        <StatCard label="Fast Moving SKUs" value={formatNumber(summary.fast_moving_sku_count)} tone="success" />
        <StatCard label="Slow Moving SKUs" value={formatNumber(summary.slow_moving_sku_count)} tone="warning" />
        <StatCard label="Dead Stock SKUs" value={formatNumber(summary.dead_stock_sku_count)} tone="danger" />
        <StatCard label="Overdue Stock" value={formatNumber(summary.overdue_stock_count)} tone="danger" />
        <StatCard label="Upcoming Deadlines" value={formatNumber(summary.upcoming_deadline_count)} tone="warning" />
        <StatCard label="Open Alerts" value={formatNumber(summary.open_alert_count)} tone="warning" />
        <StatCard label="Sales (30d)" value={formatCurrency(summary.recent_sales_total_30d)} />
        <StatCard
          label="Data Quality Score"
          value={`${summary.data_quality_score}%`}
          tone={summary.data_quality_score >= 90 ? "success" : summary.data_quality_score >= 70 ? "warning" : "danger"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <div className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-3">Inventory Aging by Bucket</div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={aging}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis dataKey="bucket_label" tick={axisTick} />
              <YAxis tick={axisTick} />
              <Tooltip formatter={(v) => (typeof v === "number" ? formatCurrency(v) : v)} {...tooltipStyle} />
              <Bar dataKey="inventory_value" fill="#4f46e5" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">Open Alerts</div>
            <Link to="/deadlines" className="text-xs text-indigo-600 hover:underline">
              View all
            </Link>
          </div>
          <div className="space-y-2 max-h-[260px] overflow-y-auto">
            {alerts.length === 0 && <div className="text-xs text-slate-400 dark:text-slate-500">No open alerts.</div>}
            {alerts.map((a) => (
              <div key={a.id} className="border border-slate-100 dark:border-slate-700/60 rounded p-2">
                <div className="flex items-center gap-2 mb-1">
                  <Badge label={a.severity} />
                  <span className="text-xs text-slate-400 dark:text-slate-500">{formatDateTime(a.created_at)}</span>
                </div>
                <div className="text-xs font-medium text-slate-800 dark:text-slate-100">{a.title}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{a.message}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 mt-4 overflow-x-auto">
        <div className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-3">Deadlines Needing Attention</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700/60">
              <th className="py-2">Scope</th>
              <th className="py-2">Deadline</th>
              <th className="py-2">Days Remaining</th>
              <th className="py-2">Status</th>
              <th className="py-2">Notes</th>
            </tr>
          </thead>
          <tbody>
            {deadlines.length === 0 && (
              <tr>
                <td colSpan={5} className="py-3 text-xs text-slate-400 dark:text-slate-500">
                  Nothing approaching or overdue.
                </td>
              </tr>
            )}
            {deadlines.map((d) => (
              <tr key={d.id} className="border-b border-slate-50 dark:border-slate-800">
                <td className="py-2">
                  {d.scope_type}: {d.scope_label ?? d.scope_id}
                </td>
                <td className="py-2">{d.deadline_date}</td>
                <td className="py-2">{d.days_remaining}</td>
                <td className="py-2">
                  <Badge label={d.status} />
                </td>
                <td className="py-2 text-slate-500 dark:text-slate-400">{d.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
