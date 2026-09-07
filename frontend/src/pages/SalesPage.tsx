import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import type { ProductVariant, Sale, Warehouse } from "../api/types";
import PageHeader from "../components/PageHeader";
import { formatCurrency, formatDate } from "../lib/format";
import { useAuth } from "../state/AuthContext";

export default function SalesPage() {
  const { hasPermission } = useAuth();
  const [sales, setSales] = useState<Sale[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.get<Sale[]>("/sales").then((r) => setSales(r.data));

  useEffect(() => {
    load();
    api.get<Warehouse[]>("/warehouses").then((r) => setWarehouses(r.data));
  }, []);

  return (
    <div>
      <PageHeader
        title="Sales"
        description="Every sale automatically reduces stock through the inventory ledger."
        actions={
          hasPermission("sales:create") && (
            <button onClick={() => setShowForm(!showForm)} className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-3 py-1.5 rounded">
              {showForm ? "Cancel" : "Record Sale"}
            </button>
          )
        }
      />

      {showForm && (
        <NewSaleForm
          warehouses={warehouses}
          onDone={() => {
            setShowForm(false);
            load();
          }}
          onError={setError}
        />
      )}
      {error && <div className="mb-4 text-sm text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800/50 rounded px-3 py-2">{error}</div>}

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-800/60">
              <th className="py-2 px-3">Invoice</th>
              <th className="py-2 px-3">Date</th>
              <th className="py-2 px-3">Party Name</th>
              <th className="py-2 px-3 text-right">Items</th>
              <th className="py-2 px-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {sales.map((s) => (
              <tr key={s.id} className="border-b border-slate-50 dark:border-slate-800">
                <td className="py-2 px-3 font-medium">{s.invoice_number}</td>
                <td className="py-2 px-3">{formatDate(s.sale_date)}</td>
                <td className="py-2 px-3 text-slate-600 dark:text-slate-300">{s.customer_name ?? "—"}</td>
                <td className="py-2 px-3 text-right">{s.items?.length ?? 0}</td>
                <td className="py-2 px-3 text-right">{formatCurrency(s.total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NewSaleForm({
  warehouses,
  onDone,
  onError,
}: {
  warehouses: Warehouse[];
  onDone: () => void;
  onError: (msg: string | null) => void;
}) {
  const [sku, setSku] = useState("");
  const [variant, setVariant] = useState<ProductVariant | null>(null);
  const [partyName, setPartyName] = useState("");
  const [warehouseId, setWarehouseId] = useState<number | "">("");
  const [quantity, setQuantity] = useState(1);
  const [unitPrice, setUnitPrice] = useState(0);
  const [saleDate, setSaleDate] = useState(new Date().toISOString().slice(0, 10));
  const [submitting, setSubmitting] = useState(false);

  const lookupSku = async () => {
    const res = await api.get<ProductVariant[]>("/variants", { params: { sku } });
    if (res.data.length > 0) {
      setVariant(res.data[0]);
      setUnitPrice(res.data[0].selling_price ?? 0);
    } else {
      onError(`No SKU found matching '${sku}'`);
    }
  };

  const submit = async () => {
    if (!variant || !warehouseId) {
      onError("Select a valid SKU and warehouse first.");
      return;
    }
    setSubmitting(true);
    onError(null);
    try {
      await api.post("/sales", {
        warehouse_id: warehouseId,
        party_name: partyName || undefined,
        sale_date: saleDate,
        items: [{ variant_id: variant.id, quantity, unit_price: unitPrice }],
      });
      onDone();
    } catch (e) {
      onError(apiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-4 mb-4">
      <div className="grid grid-cols-2 md:grid-cols-7 gap-3 items-end">
        <div className="col-span-2">
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">SKU</label>
          <div className="flex gap-1">
            <input value={sku} onChange={(e) => setSku(e.target.value)} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full" />
            <button onClick={lookupSku} className="text-xs border border-slate-300 dark:border-slate-600 rounded px-2 hover:bg-slate-50 dark:hover:bg-slate-800/60">
              Find
            </button>
          </div>
          {variant && <div className="text-[11px] text-emerald-600 mt-1">{variant.sku} found</div>}
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Party Name</label>
          <input
            value={partyName}
            onChange={(e) => setPartyName(e.target.value)}
            placeholder="Walk-in / optional"
            className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Warehouse</label>
          <select value={warehouseId} onChange={(e) => setWarehouseId(Number(e.target.value))} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full">
            <option value="">Select…</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Date</label>
          <input type="date" value={saleDate} onChange={(e) => setSaleDate(e.target.value)} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Quantity</label>
          <input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Unit Price</label>
          <input type="number" min={0} value={unitPrice} onChange={(e) => setUnitPrice(Number(e.target.value))} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full" />
        </div>
      </div>
      <button
        onClick={submit}
        disabled={submitting}
        className="mt-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded"
      >
        {submitting ? "Saving…" : "Save Sale"}
      </button>
    </div>
  );
}
