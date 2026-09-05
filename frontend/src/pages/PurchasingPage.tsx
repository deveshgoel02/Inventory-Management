import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import type { ProductVariant, PurchaseOrder, Supplier, Warehouse } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { formatDate } from "../lib/format";
import { useAuth } from "../state/AuthContext";

export default function PurchasingPage() {
  const { hasPermission } = useAuth();
  const [pos, setPos] = useState<PurchaseOrder[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.get<PurchaseOrder[]>("/purchase-orders").then((r) => setPos(r.data));

  useEffect(() => {
    load();
    api.get<Supplier[]>("/suppliers").then((r) => setSuppliers(r.data));
    api.get<Warehouse[]>("/warehouses").then((r) => setWarehouses(r.data));
  }, []);

  return (
    <div>
      <PageHeader
        title="Purchasing"
        description="Purchase orders and supplier lead times feed directly into the AI recommendation engine's 'incoming stock' calculation."
        actions={
          hasPermission("purchase:manage") && (
            <button onClick={() => setShowForm(!showForm)} className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-3 py-1.5 rounded">
              {showForm ? "Cancel" : "New Purchase Order"}
            </button>
          )
        }
      />

      {showForm && (
        <NewPoForm
          suppliers={suppliers}
          warehouses={warehouses}
          onDone={() => {
            setShowForm(false);
            load();
          }}
          onError={setError}
        />
      )}
      {error && <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
              <th className="py-2 px-3">PO Number</th>
              <th className="py-2 px-3">Order Date</th>
              <th className="py-2 px-3">Expected</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3 text-right">Items</th>
            </tr>
          </thead>
          <tbody>
            {pos.map((po) => (
              <tr key={po.id} className="border-b border-slate-50">
                <td className="py-2 px-3 font-medium">{po.po_number}</td>
                <td className="py-2 px-3">{formatDate(po.order_date)}</td>
                <td className="py-2 px-3">{formatDate(po.expected_date)}</td>
                <td className="py-2 px-3">
                  <Badge label={po.status} />
                </td>
                <td className="py-2 px-3 text-right">{po.items?.length ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-sm font-semibold text-slate-800 mb-2">Suppliers</div>
      <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
              <th className="py-2 px-3">Name</th>
              <th className="py-2 px-3">Phone</th>
              <th className="py-2 px-3 text-right">Lead Time (days)</th>
            </tr>
          </thead>
          <tbody>
            {suppliers.map((s) => (
              <tr key={s.id} className="border-b border-slate-50">
                <td className="py-2 px-3">{s.name}</td>
                <td className="py-2 px-3">{s.phone ?? "—"}</td>
                <td className="py-2 px-3 text-right">{s.lead_time_days ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NewPoForm({
  suppliers,
  warehouses,
  onDone,
  onError,
}: {
  suppliers: Supplier[];
  warehouses: Warehouse[];
  onDone: () => void;
  onError: (msg: string | null) => void;
}) {
  const [supplierId, setSupplierId] = useState<number | "">("");
  const [warehouseId, setWarehouseId] = useState<number | "">("");
  const [orderDate, setOrderDate] = useState(new Date().toISOString().slice(0, 10));
  const [sku, setSku] = useState("");
  const [variant, setVariant] = useState<ProductVariant | null>(null);
  const [quantity, setQuantity] = useState(10);
  const [unitCost, setUnitCost] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const lookupSku = async () => {
    const res = await api.get<ProductVariant[]>("/variants", { params: { sku } });
    if (res.data.length > 0) {
      setVariant(res.data[0]);
      setUnitCost(res.data[0].purchase_cost ?? 0);
    } else {
      onError(`No SKU found matching '${sku}'`);
    }
  };

  const submit = async () => {
    if (!supplierId || !warehouseId || !variant) {
      onError("Select a supplier, warehouse, and a valid SKU.");
      return;
    }
    setSubmitting(true);
    onError(null);
    try {
      await api.post("/purchase-orders", {
        supplier_id: supplierId,
        warehouse_id: warehouseId,
        order_date: orderDate,
        items: [{ variant_id: variant.id, quantity_ordered: quantity, unit_cost: unitCost }],
      });
      onDone();
    } catch (e) {
      onError(apiErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4 mb-4">
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 items-end">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Supplier</label>
          <select value={supplierId} onChange={(e) => setSupplierId(Number(e.target.value))} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full">
            <option value="">Select…</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Warehouse</label>
          <select value={warehouseId} onChange={(e) => setWarehouseId(Number(e.target.value))} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full">
            <option value="">Select…</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Order Date</label>
          <input type="date" value={orderDate} onChange={(e) => setOrderDate(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">SKU</label>
          <div className="flex gap-1">
            <input value={sku} onChange={(e) => setSku(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
            <button onClick={lookupSku} className="text-xs border border-slate-300 rounded px-2 hover:bg-slate-50">
              Find
            </button>
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Quantity</label>
          <input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Unit Cost</label>
          <input type="number" min={0} value={unitCost} onChange={(e) => setUnitCost(Number(e.target.value))} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
        </div>
      </div>
      <button onClick={submit} disabled={submitting} className="mt-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded">
        {submitting ? "Saving…" : "Create Purchase Order"}
      </button>
    </div>
  );
}
