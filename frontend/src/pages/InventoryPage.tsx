import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Brand, CurrentStockRow, Warehouse } from "../api/types";
import PageHeader from "../components/PageHeader";
import { formatCurrency, formatNumber } from "../lib/format";

export default function InventoryPage() {
  const [rows, setRows] = useState<CurrentStockRow[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [brandId, setBrandId] = useState<string>("");
  const [warehouseId, setWarehouseId] = useState<string>("");
  const [sku, setSku] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Brand[]>("/brands").then((r) => setBrands(r.data));
    api.get<Warehouse[]>("/warehouses").then((r) => setWarehouses(r.data));
  }, []);

  const load = () => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (brandId) params.brand_id = brandId;
    if (warehouseId) params.warehouse_id = warehouseId;
    if (sku) params.sku = sku;
    api
      .get<CurrentStockRow[]>("/inventory/current-stock", { params })
      .then((r) => setRows(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(load, [brandId, warehouseId]);

  const totalUnits = rows.reduce((s, r) => s + r.quantity_on_hand, 0);
  const totalCost = rows.reduce((s, r) => s + r.inventory_cost_value, 0);
  const totalSelling = rows.reduce((s, r) => s + r.inventory_selling_value, 0);

  return (
    <div>
      <PageHeader title="Inventory" description="Live stock on hand, derived from the transaction ledger — never a manually maintained count." />

      <div className="flex flex-wrap gap-3 mb-4">
        <select value={brandId} onChange={(e) => setBrandId(e.target.value)} className="border border-slate-300 rounded px-3 py-1.5 text-sm">
          <option value="">All Brands</option>
          {brands.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <select value={warehouseId} onChange={(e) => setWarehouseId(e.target.value)} className="border border-slate-300 rounded px-3 py-1.5 text-sm">
          <option value="">All Warehouses</option>
          {warehouses.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
        <input
          value={sku}
          onChange={(e) => setSku(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load()}
          placeholder="Search SKU…"
          className="border border-slate-300 rounded px-3 py-1.5 text-sm w-56"
        />
        <button onClick={load} className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-3 py-1.5 rounded">
          Search
        </button>
        <a
          href={`/api/reports/inventory/export?format=csv`}
          className="ml-auto text-sm border border-slate-300 rounded px-3 py-1.5 hover:bg-slate-50"
        >
          Export CSV
        </a>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="text-xs text-slate-500">Units shown</div>
          <div className="text-lg font-semibold">{formatNumber(totalUnits)}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="text-xs text-slate-500">Cost value</div>
          <div className="text-lg font-semibold">{formatCurrency(totalCost)}</div>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-3">
          <div className="text-xs text-slate-500">Selling value</div>
          <div className="text-lg font-semibold">{formatCurrency(totalSelling)}</div>
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
              <th className="py-2 px-3 text-right">Qty</th>
              <th className="py-2 px-3 text-right">Cost Value</th>
              <th className="py-2 px-3 text-right">Selling Value</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="py-4 px-3 text-slate-400">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={7} className="py-4 px-3 text-slate-400">
                  No stock found for these filters.
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={`${r.variant_id}-${r.warehouse_id}`} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="py-2 px-3">
                  <Link to={`/inventory/${r.variant_id}`} className="text-indigo-600 hover:underline font-medium">
                    {r.sku}
                  </Link>
                </td>
                <td className="py-2 px-3">{r.product_name}</td>
                <td className="py-2 px-3">{r.brand_name}</td>
                <td className="py-2 px-3">{r.warehouse_name}</td>
                <td className="py-2 px-3 text-right">{formatNumber(r.quantity_on_hand)}</td>
                <td className="py-2 px-3 text-right">{formatCurrency(r.inventory_cost_value)}</td>
                <td className="py-2 px-3 text-right">{formatCurrency(r.inventory_selling_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
