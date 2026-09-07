import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { BusinessInsight, MovementClassificationRow } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { formatNumber } from "../lib/format";

export default function AnalyticsPage() {
  const [insights, setInsights] = useState<BusinessInsight[]>([]);
  const [classification, setClassification] = useState<MovementClassificationRow[]>([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.get<BusinessInsight[]>("/insights").then((r) => setInsights(r.data));
    api.get<MovementClassificationRow[]>("/classification").then((r) => setClassification(r.data));
  }, []);

  const filtered = filter ? classification.filter((c) => c.classification === filter) : classification;
  const classes = Array.from(new Set(classification.map((c) => c.classification)));

  return (
    <div>
      <PageHeader title="Analytics & Insights" description="Auto-generated business observations, backed by live ledger and sales data — nothing fabricated." />

      <div className="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-2">Business Insights</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
        {insights.map((i) => (
          <div key={i.id} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Badge label={i.severity} />
              <span className="text-[11px] text-slate-400 dark:text-slate-500 uppercase">{i.category.replace(/_/g, " ")}</span>
            </div>
            <div className="text-sm text-slate-800 dark:text-slate-100">{i.text}</div>
          </div>
        ))}
        {insights.length === 0 && <div className="text-xs text-slate-400 dark:text-slate-500">No notable patterns detected yet.</div>}
      </div>

      <div className="flex items-center justify-between mb-2">
        <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">Movement Classification</div>
        <div className="flex gap-1">
          <button onClick={() => setFilter("")} className={`text-xs px-2 py-1 rounded border ${filter === "" ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30" : "border-slate-200 dark:border-slate-700"}`}>
            All
          </button>
          {classes.map((c) => (
            <button key={c} onClick={() => setFilter(c)} className={`text-xs px-2 py-1 rounded border ${filter === c ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30" : "border-slate-200 dark:border-slate-700"}`}>
              {c.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-800/60">
              <th className="py-2 px-3">SKU</th>
              <th className="py-2 px-3">Product</th>
              <th className="py-2 px-3">Classification</th>
              <th className="py-2 px-3 text-right">Velocity/day</th>
              <th className="py-2 px-3 text-right">Days of Cover</th>
              <th className="py-2 px-3 text-right">Current Stock</th>
              <th className="py-2 px-3">Why</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.variant_id} className="border-b border-slate-50 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60">
                <td className="py-2 px-3">
                  <Link to={`/inventory/${c.variant_id}`} className="text-indigo-600 hover:underline font-medium">
                    {c.sku}
                  </Link>
                </td>
                <td className="py-2 px-3">
                  {c.product_name} <span className="text-slate-400 dark:text-slate-500">({c.brand_name})</span>
                </td>
                <td className="py-2 px-3">
                  <Badge label={c.classification} />
                </td>
                <td className="py-2 px-3 text-right">{formatNumber(c.sales_velocity_per_day)}</td>
                <td className="py-2 px-3 text-right">{c.days_of_cover ?? "—"}</td>
                <td className="py-2 px-3 text-right">{formatNumber(c.current_stock)}</td>
                <td className="py-2 px-3 text-xs text-slate-500 dark:text-slate-400 max-w-xs">{c.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
