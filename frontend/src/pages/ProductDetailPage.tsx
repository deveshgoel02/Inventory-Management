import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, apiErrorMessage } from "../api/client";
import type { ForecastResult, ProductVariantDetail, StockHealth } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { formatCurrency, formatDateTime, formatNumber } from "../lib/format";

interface LedgerEntry {
  id: number;
  transaction_type: string;
  quantity: number;
  transaction_date: string;
  unit_cost: number | null;
  unit_price: number | null;
  reference_type: string | null;
  notes: string | null;
}

export default function ProductDetailPage() {
  const { variantId } = useParams();
  const [detail, setDetail] = useState<ProductVariantDetail | null>(null);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [forecast, setForecast] = useState<ForecastResult | null>(null);
  const [health, setHealth] = useState<StockHealth | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!variantId) return;
    api.get<ProductVariantDetail>(`/variants/${variantId}`).then((r) => setDetail(r.data));
    api.get<LedgerEntry[]>(`/inventory/ledger/${variantId}`).then((r) => setLedger(r.data));
    api
      .get<ForecastResult>(`/forecasting/${variantId}`)
      .then((r) => setForecast(r.data))
      .catch((e) => setError(apiErrorMessage(e)));
    api.get<StockHealth>(`/stock-health/${variantId}`).then((r) => setHealth(r.data));
  }, [variantId]);

  if (!detail) return <div className="text-slate-400 text-sm">Loading…</div>;

  return (
    <div>
      <PageHeader
        title={`${detail.sku} — ${detail.product_name}`}
        description={`${detail.brand_name}${detail.category_name ? " · " + detail.category_name : ""}${detail.size ? " · Size " + detail.size : ""}${detail.color ? " · " + detail.color : ""}`}
        actions={
          <Link to="/inventory" className="text-sm border border-slate-300 rounded px-3 py-1.5 hover:bg-slate-50">
            Back to Inventory
          </Link>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="text-xs text-slate-500">Current Stock</div>
          <div className="text-lg font-semibold">{formatNumber(detail.current_stock)}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="text-xs text-slate-500">Purchase Cost</div>
          <div className="text-lg font-semibold">{formatCurrency(detail.purchase_cost)}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="text-xs text-slate-500">Selling Price</div>
          <div className="text-lg font-semibold">{formatCurrency(detail.selling_price)}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="text-xs text-slate-500">MRP</div>
          <div className="text-lg font-semibold">{formatCurrency(detail.mrp)}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-5">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">AI Demand Forecast</div>
          {error && <div className="text-xs text-red-600">{error}</div>}
          {forecast && (
            <div>
              <div className="flex gap-2 mb-2">
                <Badge label={forecast.confidence} />
                <Badge label={forecast.risk_level} />
                <span className="text-xs text-slate-400 self-center">model: {forecast.model_name}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 mb-3">
                {Object.entries(forecast.forecasts).map(([horizon, qty]) => (
                  <div key={horizon} className="bg-slate-50 rounded p-2 text-center">
                    <div className="text-xs text-slate-500">{horizon}-day forecast</div>
                    <div className="text-base font-semibold">{formatNumber(qty)}</div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">{forecast.explanation}</p>
              <p className="text-[11px] text-slate-400 mt-2 italic">
                Estimate based on historical data and configured assumptions — not a guarantee.
              </p>
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">Stock Health</div>
          {health && (
            <div>
              <div className="flex items-baseline gap-2 mb-3">
                <div className="text-3xl font-bold">{health.score}</div>
                <div className="text-sm text-slate-500">/ 100 — {health.status}</div>
              </div>
              <div className="space-y-2">
                {health.factors.map((f) => (
                  <div key={f.name}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="font-medium text-slate-700">{f.name}</span>
                      <span className="text-slate-500">
                        {f.points}/{f.max_points}
                      </span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500"
                        style={{ width: `${(f.points / f.max_points) * 100}%` }}
                      />
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{f.detail}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
        <div className="text-sm font-semibold text-slate-800 p-4 pb-0">Inventory Ledger (most recent first)</div>
        <table className="w-full text-sm mt-2">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
              <th className="py-2 px-3">Date</th>
              <th className="py-2 px-3">Type</th>
              <th className="py-2 px-3 text-right">Quantity</th>
              <th className="py-2 px-3 text-right">Unit Cost</th>
              <th className="py-2 px-3 text-right">Unit Price</th>
              <th className="py-2 px-3">Reference</th>
              <th className="py-2 px-3">Notes</th>
            </tr>
          </thead>
          <tbody>
            {ledger.slice(0, 100).map((t) => (
              <tr key={t.id} className="border-b border-slate-50">
                <td className="py-2 px-3">{formatDateTime(t.transaction_date)}</td>
                <td className="py-2 px-3">
                  <Badge label={t.transaction_type} />
                </td>
                <td className="py-2 px-3 text-right">{formatNumber(t.quantity)}</td>
                <td className="py-2 px-3 text-right">{formatCurrency(t.unit_cost)}</td>
                <td className="py-2 px-3 text-right">{formatCurrency(t.unit_price)}</td>
                <td className="py-2 px-3 text-slate-500">{t.reference_type}</td>
                <td className="py-2 px-3 text-slate-500">{t.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
