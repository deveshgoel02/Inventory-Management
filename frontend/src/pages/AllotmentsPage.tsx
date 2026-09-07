import { Fragment, useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import type { ProductVariant, SalesAllotment, SalesAllotmentDetail, SalesmanBrief, Warehouse } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { formatDate } from "../lib/format";
import { useAuth } from "../state/AuthContext";

export default function AllotmentsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("allotment:manage");
  const [allotments, setAllotments] = useState<SalesAllotment[]>([]);
  const [salesmen, setSalesmen] = useState<SalesmanBrief[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<SalesAllotmentDetail | null>(null);

  const load = () => api.get<SalesAllotment[]>("/allotments").then((r) => setAllotments(r.data));

  useEffect(() => {
    load();
    api.get<Warehouse[]>("/warehouses").then((r) => setWarehouses(r.data));
    if (canManage) {
      api.get<SalesmanBrief[]>("/allotments/salesmen").then((r) => setSalesmen(r.data));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleExpand = async (a: SalesAllotment) => {
    if (expandedId === a.id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(a.id);
    const res = await api.get<SalesAllotmentDetail>(`/allotments/${a.id}`);
    setDetail(res.data);
  };

  const cancelAllotment = async (a: SalesAllotment) => {
    await api.patch(`/allotments/${a.id}`, { is_active: false });
    load();
    if (expandedId === a.id) {
      const res = await api.get<SalesAllotmentDetail>(`/allotments/${a.id}`);
      setDetail(res.data);
    }
  };

  return (
    <div>
      <PageHeader
        title="Salesman Allotments"
        description="Assign a salesman a target quantity for a SKU, then track how much of it they've actually sold."
        actions={
          canManage && (
            <button onClick={() => setShowForm(!showForm)} className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-3 py-1.5 rounded">
              {showForm ? "Cancel" : "New Allotment"}
            </button>
          )
        }
      />

      {showForm && canManage && (
        <NewAllotmentForm
          salesmen={salesmen}
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
              <th className="py-2 px-3">Salesman</th>
              <th className="py-2 px-3">SKU / Product</th>
              <th className="py-2 px-3">Warehouse</th>
              <th className="py-2 px-3 text-right">Allotted</th>
              <th className="py-2 px-3 text-right">Executed</th>
              <th className="py-2 px-3 text-right">Remaining</th>
              <th className="py-2 px-3">Progress</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3">Due</th>
              <th className="py-2 px-3"></th>
            </tr>
          </thead>
          <tbody>
            {allotments.map((a) => (
              <Fragment key={a.id}>
                <tr className="border-b border-slate-50 dark:border-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60" onClick={() => toggleExpand(a)}>
                  <td className="py-2 px-3 font-medium">{a.salesman_name}</td>
                  <td className="py-2 px-3">
                    <div>{a.sku}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">{a.product_name}</div>
                  </td>
                  <td className="py-2 px-3 text-slate-600 dark:text-slate-300">{a.warehouse_name ?? "Any"}</td>
                  <td className="py-2 px-3 text-right">{a.allotted_quantity}</td>
                  <td className="py-2 px-3 text-right">{a.executed_quantity}</td>
                  <td className="py-2 px-3 text-right">{a.remaining_quantity}</td>
                  <td className="py-2 px-3">
                    <div className="w-24 h-2 bg-slate-100 dark:bg-slate-700 rounded overflow-hidden">
                      <div
                        className={a.fulfillment_status === "FULFILLED" ? "h-full bg-emerald-500" : "h-full bg-indigo-500"}
                        style={{ width: `${Math.min(100, a.completion_pct)}%` }}
                      />
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{a.completion_pct}%</div>
                  </td>
                  <td className="py-2 px-3">
                    <Badge label={a.fulfillment_status} />
                  </td>
                  <td className="py-2 px-3 text-slate-600 dark:text-slate-300">{a.due_date ? formatDate(a.due_date) : "—"}</td>
                  <td className="py-2 px-3 text-right">
                    {canManage && a.is_active && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          cancelAllotment(a);
                        }}
                        className="text-xs text-red-600 hover:underline"
                      >
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
                {expandedId === a.id && detail && (
                  <tr className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-100 dark:border-slate-700/60">
                    <td colSpan={10} className="py-3 px-3">
                      <div className="text-xs font-medium text-slate-600 dark:text-slate-300 mb-2">
                        Execution detail — allotted {formatDate(detail.allotted_date)}
                        {detail.due_date ? ` through ${formatDate(detail.due_date)}` : ""}
                        {detail.notes ? ` · ${detail.notes}` : ""}
                      </div>
                      {detail.contributing_sales.length === 0 ? (
                        <div className="text-sm text-slate-500 dark:text-slate-400">No sales recorded against this allotment yet.</div>
                      ) : (
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="text-left text-slate-500 dark:text-slate-400">
                              <th className="py-1 pr-3">Invoice</th>
                              <th className="py-1 pr-3">Date</th>
                              <th className="py-1 pr-3 text-right">Quantity</th>
                              <th className="py-1 pr-3 text-right">Unit Price</th>
                            </tr>
                          </thead>
                          <tbody>
                            {detail.contributing_sales.map((s) => (
                              <tr key={s.sale_id} className="border-t border-slate-100 dark:border-slate-700/60">
                                <td className="py-1 pr-3">{s.invoice_number}</td>
                                <td className="py-1 pr-3">{formatDate(s.sale_date)}</td>
                                <td className="py-1 pr-3 text-right">{s.quantity}</td>
                                <td className="py-1 pr-3 text-right">₹{s.unit_price}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {allotments.length === 0 && (
              <tr>
                <td colSpan={10} className="py-6 px-3 text-center text-slate-400 dark:text-slate-500">
                  No allotments yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NewAllotmentForm({
  salesmen,
  warehouses,
  onDone,
  onError,
}: {
  salesmen: SalesmanBrief[];
  warehouses: Warehouse[];
  onDone: () => void;
  onError: (msg: string | null) => void;
}) {
  const [salesmanId, setSalesmanId] = useState<number | "">("");
  const [sku, setSku] = useState("");
  const [variant, setVariant] = useState<ProductVariant | null>(null);
  const [warehouseId, setWarehouseId] = useState<number | "">("");
  const [quantity, setQuantity] = useState(1);
  const [allottedDate, setAllottedDate] = useState(new Date().toISOString().slice(0, 10));
  const [dueDate, setDueDate] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const lookupSku = async () => {
    const res = await api.get<ProductVariant[]>("/variants", { params: { sku } });
    if (res.data.length > 0) {
      setVariant(res.data[0]);
    } else {
      onError(`No SKU found matching '${sku}'`);
    }
  };

  const submit = async () => {
    if (!salesmanId || !variant) {
      onError("Select a salesman and a valid SKU first.");
      return;
    }
    setSubmitting(true);
    onError(null);
    try {
      await api.post("/allotments", {
        salesman_id: salesmanId,
        variant_id: variant.id,
        warehouse_id: warehouseId || undefined,
        allotted_quantity: quantity,
        allotted_date: allottedDate,
        due_date: dueDate || undefined,
        notes: notes || undefined,
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Salesman</label>
          <select value={salesmanId} onChange={(e) => setSalesmanId(Number(e.target.value))} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full">
            <option value="">Select…</option>
            {salesmen.map((s) => (
              <option key={s.id} value={s.id}>
                {s.full_name} ({s.role_name})
              </option>
            ))}
          </select>
        </div>
        <div className="col-span-2 md:col-span-1">
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
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Warehouse</label>
          <select value={warehouseId} onChange={(e) => setWarehouseId(Number(e.target.value))} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full">
            <option value="">Any</option>
            {warehouses.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Quantity</label>
          <input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Allotted From</label>
          <input type="date" value={allottedDate} onChange={(e) => setAllottedDate(e.target.value)} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Due Date (optional)</label>
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div className="col-span-2 md:col-span-4">
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Notes (optional)</label>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} className="border border-slate-300 dark:border-slate-600 rounded px-2 py-1.5 text-sm w-full" />
        </div>
      </div>
      <button
        onClick={submit}
        disabled={submitting}
        className="mt-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded"
      >
        {submitting ? "Saving…" : "Create Allotment"}
      </button>
    </div>
  );
}
