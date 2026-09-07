import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ForecastResult, ProductVariant } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { formatNumber } from "../lib/format";
import { useAuth } from "../state/AuthContext";

interface Row extends ForecastResult {
  variant: ProductVariant;
}

export default function ForecastingPage() {
  const { hasPermission } = useAuth();
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    setLoading(true);
    const variantsRes = await api.get<ProductVariant[]>("/variants");
    const variants = variantsRes.data;
    const forecasts = await Promise.all(
      variants.map((v) =>
        api
          .get<ForecastResult>(`/forecasting/${v.id}`)
          .then((r) => ({ ...r.data, variant: v }))
          .catch(() => null)
      )
    );
    setRows(forecasts.filter((f): f is Row => f !== null));
    setLoading(false);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshAll = async () => {
    setRefreshing(true);
    await api.post("/forecasting/refresh");
    await load();
    setRefreshing(false);
  };

  return (
    <div>
      <PageHeader
        title="AI Forecasting"
        description="Statistical demand forecasts per SKU — model choice depends on how much sales history exists. Estimates, not guarantees."
        actions={
          hasPermission("ai:manage") && (
            <button onClick={refreshAll} disabled={refreshing} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-3 py-1.5 rounded">
              {refreshing ? "Refreshing…" : "Refresh Forecasts"}
            </button>
          )
        }
      />

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-800/60">
              <th className="py-2 px-3">SKU</th>
              <th className="py-2 px-3">Model</th>
              <th className="py-2 px-3 text-right">Hist. Avg/day</th>
              <th className="py-2 px-3 text-right">Recent Avg/day</th>
              <th className="py-2 px-3 text-right">30d</th>
              <th className="py-2 px-3 text-right">60d</th>
              <th className="py-2 px-3 text-right">90d</th>
              <th className="py-2 px-3">Confidence</th>
              <th className="py-2 px-3">Risk</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={9} className="py-4 px-3 text-slate-400 dark:text-slate-500">
                  Loading forecasts…
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.variant_id} className="border-b border-slate-50 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/60">
                <td className="py-2 px-3">
                  <Link to={`/inventory/${r.variant_id}`} className="text-indigo-600 hover:underline font-medium">
                    {r.sku}
                  </Link>
                </td>
                <td className="py-2 px-3 text-slate-500 dark:text-slate-400 text-xs">{r.model_name.replace(/_/g, " ")}</td>
                <td className="py-2 px-3 text-right">{formatNumber(r.historical_avg_daily_sales)}</td>
                <td className="py-2 px-3 text-right">{formatNumber(r.recent_avg_daily_sales)}</td>
                <td className="py-2 px-3 text-right">{formatNumber(r.forecasts["30"])}</td>
                <td className="py-2 px-3 text-right">{formatNumber(r.forecasts["60"])}</td>
                <td className="py-2 px-3 text-right">{formatNumber(r.forecasts["90"])}</td>
                <td className="py-2 px-3">
                  <Badge label={r.confidence} />
                </td>
                <td className="py-2 px-3">
                  <Badge label={r.risk_level} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400 dark:text-slate-500 mt-3 italic">
        Recommendations are estimates based on historical data and configured assumptions. Click any SKU for the full explanation and accuracy backtest.
      </p>
    </div>
  );
}
