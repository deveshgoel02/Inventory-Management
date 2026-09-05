import { Fragment, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Recommendation } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { formatNumber } from "../lib/format";
import { useAuth } from "../state/AuthContext";

export default function RecommendationsPage() {
  const { hasPermission } = useAuth();
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);

  const load = () => api.get<Recommendation[]>("/recommendations").then((r) => setRecs(r.data));

  useEffect(() => {
    load();
  }, []);

  const generate = async () => {
    setGenerating(true);
    await api.post("/recommendations/generate");
    await load();
    setGenerating(false);
  };

  const review = async (id: number, decision: "ACCEPTED" | "DISMISSED") => {
    await api.post(`/recommendations/${id}/review`, null, { params: { decision } });
    load();
  };

  return (
    <div>
      <PageHeader
        title="Purchase Recommendations"
        description="Decision support only — nothing here places an order automatically. Review the reasoning, then accept or dismiss."
        actions={
          hasPermission("ai:manage") && (
            <button onClick={generate} disabled={generating} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-3 py-1.5 rounded">
              {generating ? "Generating…" : "Generate Recommendations"}
            </button>
          )
        }
      />

      <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
              <th className="py-2 px-3">SKU</th>
              <th className="py-2 px-3">Product</th>
              <th className="py-2 px-3 text-right">Current Stock</th>
              <th className="py-2 px-3 text-right">Suggested Order</th>
              <th className="py-2 px-3">Confidence</th>
              <th className="py-2 px-3">Risk</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3"></th>
            </tr>
          </thead>
          <tbody>
            {recs.map((r) => (
              <Fragment key={r.id}>
                <tr className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-2 px-3 font-medium">{r.sku}</td>
                  <td className="py-2 px-3">
                    {r.product_name} <span className="text-slate-400">({r.brand_name})</span>
                  </td>
                  <td className="py-2 px-3 text-right">{formatNumber(r.current_stock)}</td>
                  <td className="py-2 px-3 text-right font-semibold">{formatNumber(r.recommended_order_qty)}</td>
                  <td className="py-2 px-3">
                    <Badge label={r.confidence} />
                  </td>
                  <td className="py-2 px-3">
                    <Badge label={r.risk_level} />
                  </td>
                  <td className="py-2 px-3">
                    <Badge label={r.status} />
                  </td>
                  <td className="py-2 px-3 text-right whitespace-nowrap">
                    <button
                      onClick={() => setExpanded(expanded === r.id ? null : r.id)}
                      className="text-xs text-indigo-600 hover:underline mr-2"
                    >
                      {expanded === r.id ? "Hide" : "Why?"}
                    </button>
                    {hasPermission("ai:manage") && r.status === "PENDING" && (
                      <>
                        <button onClick={() => review(r.id, "ACCEPTED")} className="text-xs text-emerald-600 hover:underline mr-2">
                          Accept
                        </button>
                        <button onClick={() => review(r.id, "DISMISSED")} className="text-xs text-slate-500 hover:underline">
                          Dismiss
                        </button>
                      </>
                    )}
                  </td>
                </tr>
                {expanded === r.id && (
                  <tr className="bg-slate-50 border-b border-slate-100">
                    <td colSpan={8} className="py-3 px-3">
                      <div className="text-xs text-slate-600 space-y-1">
                        <div>
                          <span className="font-medium">Formula:</span> {String(r.reasoning.formula)}
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
                          <div>
                            <span className="text-slate-400">Daily sales rate:</span> {String(r.reasoning.daily_sales_rate)}
                          </div>
                          <div>
                            <span className="text-slate-400">Lead time (days):</span> {String(r.reasoning.lead_time_days)}
                          </div>
                          <div>
                            <span className="text-slate-400">Forecast demand (lead time):</span>{" "}
                            {String(r.reasoning.forecast_demand_during_lead_time)}
                          </div>
                          <div>
                            <span className="text-slate-400">Safety stock:</span> {String(r.reasoning.safety_stock_units)}
                          </div>
                          <div>
                            <span className="text-slate-400">Incoming stock:</span> {String(r.reasoning.incoming_stock)}
                          </div>
                          <div>
                            <span className="text-slate-400">Days of cover:</span>{" "}
                            {String(r.reasoning.days_of_cover_at_current_stock ?? "n/a")}
                          </div>
                          <div>
                            <span className="text-slate-400">MOQ applied:</span>{" "}
                            {String(r.reasoning.minimum_order_quantity_applied ?? "none")}
                          </div>
                        </div>
                        <div className="pt-1 text-slate-500">{String(r.reasoning.forecast_explanation)}</div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
