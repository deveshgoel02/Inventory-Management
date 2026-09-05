import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api } from "../api/client";
import type { AgingBucketRow, AgingDetailRow } from "../api/types";
import PageHeader from "../components/PageHeader";
import { formatCurrency, formatDate, formatNumber } from "../lib/format";

export default function AgingPage() {
  const [summary, setSummary] = useState<AgingBucketRow[]>([]);
  const [detail, setDetail] = useState<AgingDetailRow[]>([]);
  const [bucketFilter, setBucketFilter] = useState<string>("");

  useEffect(() => {
    api.get<AgingBucketRow[]>("/inventory/aging/summary").then((r) => setSummary(r.data));
    api.get<AgingDetailRow[]>("/inventory/aging/detail").then((r) => setDetail(r.data));
  }, []);

  const filteredDetail = bucketFilter ? detail.filter((d) => d.bucket_label === bucketFilter) : detail;

  return (
    <div>
      <PageHeader
        title="Stock Aging"
        description="Age is computed per receiving batch — a SKU with multiple lots can straddle several buckets at once."
        actions={
          <a href="/api/reports/aging/export?format=csv" className="text-sm border border-slate-300 rounded px-3 py-1.5 hover:bg-slate-50">
            Export CSV
          </a>
        }
      />

      <div className="bg-white border border-slate-200 rounded-lg p-4 mb-5">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={summary} onClick={(state) => state?.activeLabel && setBucketFilter(state.activeLabel as string)}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
            <XAxis dataKey="bucket_label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => (typeof v === "number" ? formatCurrency(v) : v)} />
            <Bar dataKey="inventory_value" fill="#4f46e5" radius={[3, 3, 0, 0]} cursor="pointer" />
          </BarChart>
        </ResponsiveContainer>
        <div className="grid grid-cols-3 md:grid-cols-7 gap-2 mt-4 text-center">
          {summary.map((b) => (
            <button
              key={b.bucket_label}
              onClick={() => setBucketFilter(bucketFilter === b.bucket_label ? "" : b.bucket_label)}
              className={`rounded p-2 border text-left ${bucketFilter === b.bucket_label ? "border-indigo-500 bg-indigo-50" : "border-slate-100"}`}
            >
              <div className="text-[11px] text-slate-500">{b.bucket_label}</div>
              <div className="text-sm font-semibold">{formatNumber(b.sku_count)} SKUs</div>
              <div className="text-[11px] text-slate-500">{formatCurrency(b.inventory_value)}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
              <th className="py-2 px-3">SKU</th>
              <th className="py-2 px-3">Product</th>
              <th className="py-2 px-3">Brand</th>
              <th className="py-2 px-3">Warehouse</th>
              <th className="py-2 px-3">Batch</th>
              <th className="py-2 px-3">Received</th>
              <th className="py-2 px-3 text-right">Age (days)</th>
              <th className="py-2 px-3 text-right">Qty</th>
              <th className="py-2 px-3 text-right">Value</th>
            </tr>
          </thead>
          <tbody>
            {filteredDetail.slice(0, 300).map((row) => (
              <tr key={row.batch_id} className="border-b border-slate-50">
                <td className="py-2 px-3 font-medium">{row.sku}</td>
                <td className="py-2 px-3">{row.product_name}</td>
                <td className="py-2 px-3">{row.brand_name}</td>
                <td className="py-2 px-3">{row.warehouse_name}</td>
                <td className="py-2 px-3">{row.batch_code}</td>
                <td className="py-2 px-3">{formatDate(row.received_date)}</td>
                <td className="py-2 px-3 text-right">{row.age_days}</td>
                <td className="py-2 px-3 text-right">{formatNumber(row.quantity)}</td>
                <td className="py-2 px-3 text-right">{formatCurrency(row.inventory_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
