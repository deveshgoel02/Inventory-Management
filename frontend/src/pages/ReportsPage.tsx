import PageHeader from "../components/PageHeader";

const REPORTS = [
  { key: "inventory", label: "Current Inventory", description: "Every SKU currently in stock, with cost and selling value." },
  { key: "aging", label: "Stock Aging", description: "Batch-level aging detail across all warehouses." },
  { key: "dead_stock", label: "Dead / Very Slow Stock", description: "SKUs classified as dead stock or very slow moving." },
  { key: "recommendations", label: "AI Purchase Recommendations", description: "The most recent recommendation generated per SKU." },
  { key: "sales", label: "Sales", description: "Sales transactions, most recent first." },
  { key: "brand_performance", label: "Brand Performance", description: "Units sold and revenue by brand." },
];

export default function ReportsPage() {
  return (
    <div>
      <PageHeader title="Reports" description="Every export reads from the same authoritative backend data shown on screen." />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {REPORTS.map((r) => (
          <div key={r.key} className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-sm font-semibold text-slate-800">{r.label}</div>
            <p className="text-xs text-slate-500 mt-1 mb-3">{r.description}</p>
            <div className="flex gap-2">
              <a href={`/api/reports/${r.key}/export?format=csv`} className="text-xs border border-slate-300 rounded px-3 py-1.5 hover:bg-slate-50">
                Export CSV
              </a>
              <a href={`/api/reports/${r.key}/export?format=xlsx`} className="text-xs border border-slate-300 rounded px-3 py-1.5 hover:bg-slate-50">
                Export Excel
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
