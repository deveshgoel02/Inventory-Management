import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { DataQualityReport } from "../api/types";
import PageHeader from "../components/PageHeader";

const LABELS: Record<string, string> = {
  products_missing_category: "Products missing category",
  variants_missing_purchase_cost: "SKUs missing purchase cost",
  variants_missing_selling_price: "SKUs missing selling price",
  sale_items_missing_cost: "Sale line items missing cost",
  duplicate_barcodes: "Duplicate barcodes",
  unexplained_stock_adjustments: "Stock adjustments without notes",
};

export default function DataQualityPage() {
  const [report, setReport] = useState<DataQualityReport | null>(null);

  useEffect(() => {
    api.get<DataQualityReport>("/data-quality").then((r) => setReport(r.data));
  }, []);

  if (!report) return <div className="text-slate-400 text-sm">Loading…</div>;

  const tone = report.score >= 90 ? "text-emerald-600" : report.score >= 70 ? "text-amber-600" : "text-red-600";

  return (
    <div>
      <PageHeader title="Data Quality Center" description="Detects gaps and inconsistencies in the data behind every calculation on this platform." />

      <div className="bg-white border border-slate-200 rounded-lg p-6 mb-6 text-center">
        <div className="text-xs text-slate-500 uppercase tracking-wide">Overall Data Quality</div>
        <div className={`text-5xl font-bold mt-1 ${tone}`}>{report.score}%</div>
      </div>

      <div className="space-y-3">
        {Object.entries(report.issue_counts).map(([key, count]) => (
          <div key={key} className="bg-white border border-slate-200 rounded-lg p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-medium text-slate-800">{LABELS[key] ?? key}</div>
              <div className={`text-sm font-semibold ${count === 0 ? "text-emerald-600" : "text-amber-600"}`}>{count}</div>
            </div>
            {count > 0 && (
              <div className="text-xs text-slate-500 max-h-24 overflow-y-auto">
                {report.issues[key]?.slice(0, 20).map((issue) => (
                  <div key={`${issue.entity}-${issue.id}`}>
                    {issue.entity} — {issue.label}
                  </div>
                ))}
                {report.issues[key]?.length > 20 && <div>…and {report.issues[key].length - 20} more</div>}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
