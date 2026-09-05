import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import type { Alert, StockDeadline } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { formatDate, formatDateTime } from "../lib/format";
import { useAuth } from "../state/AuthContext";

export default function DeadlinesPage() {
  const { hasPermission } = useAuth();
  const [deadlines, setDeadlines] = useState<StockDeadline[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDeadlines = () => api.get<StockDeadline[]>("/deadlines").then((r) => setDeadlines(r.data));
  const loadAlerts = () => api.get<Alert[]>("/alerts").then((r) => setAlerts(r.data));

  useEffect(() => {
    loadDeadlines();
    loadAlerts();
  }, []);

  const acknowledge = async (id: number) => {
    await api.post(`/alerts/${id}/acknowledge`);
    loadAlerts();
  };
  const resolve = async (id: number) => {
    await api.post(`/alerts/${id}/resolve`);
    loadAlerts();
  };

  return (
    <div>
      <PageHeader
        title="Deadlines & Alerts"
        description="Set a sell-by deadline on any SKU, product, brand, or category. Alerts de-duplicate automatically as a condition persists."
        actions={
          hasPermission("deadline:manage") && (
            <button onClick={() => setShowForm(!showForm)} className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-3 py-1.5 rounded">
              {showForm ? "Cancel" : "New Deadline"}
            </button>
          )
        }
      />

      {showForm && (
        <NewDeadlineForm
          onDone={() => {
            setShowForm(false);
            loadDeadlines();
            loadAlerts();
          }}
          onError={setError}
        />
      )}
      {error && <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <div className="text-sm font-semibold text-slate-800 mb-2">Stock Deadlines</div>
          <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
                  <th className="py-2 px-3">Scope</th>
                  <th className="py-2 px-3">Deadline</th>
                  <th className="py-2 px-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {deadlines.map((d) => (
                  <tr key={d.id} className="border-b border-slate-50">
                    <td className="py-2 px-3">
                      {d.scope_type}: {d.scope_label ?? d.scope_id}
                      {d.notes && <div className="text-[11px] text-slate-400">{d.notes}</div>}
                    </td>
                    <td className="py-2 px-3">
                      {formatDate(d.deadline_date)}
                      {d.days_remaining !== null && (
                        <div className="text-[11px] text-slate-400">{d.days_remaining} day(s) remaining</div>
                      )}
                    </td>
                    <td className="py-2 px-3">
                      <Badge label={d.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="text-sm font-semibold text-slate-800 mb-2">Alerts</div>
          <div className="space-y-2">
            {alerts.map((a) => (
              <div key={a.id} className="bg-white border border-slate-200 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Badge label={a.severity} />
                    <Badge label={a.status} />
                  </div>
                  <span className="text-[11px] text-slate-400">{formatDateTime(a.created_at)}</span>
                </div>
                <div className="text-sm font-medium text-slate-800">{a.title}</div>
                <div className="text-xs text-slate-500 mb-2">{a.message}</div>
                {a.status !== "RESOLVED" && hasPermission("alert:manage") && (
                  <div className="flex gap-2">
                    {a.status === "OPEN" && (
                      <button onClick={() => acknowledge(a.id)} className="text-xs border border-slate-300 rounded px-2 py-1 hover:bg-slate-50">
                        Acknowledge
                      </button>
                    )}
                    <button onClick={() => resolve(a.id)} className="text-xs border border-slate-300 rounded px-2 py-1 hover:bg-slate-50">
                      Resolve
                    </button>
                  </div>
                )}
              </div>
            ))}
            {alerts.length === 0 && <div className="text-xs text-slate-400">No alerts.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

function NewDeadlineForm({ onDone, onError }: { onDone: () => void; onError: (msg: string | null) => void }) {
  const [scopeType, setScopeType] = useState("SKU");
  const [scopeId, setScopeId] = useState("");
  const [skuLookup, setSkuLookup] = useState("");
  const [deadlineDate, setDeadlineDate] = useState("");
  const [warningDays, setWarningDays] = useState(14);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const lookupSku = async () => {
    const res = await api.get("/variants", { params: { sku: skuLookup } });
    if (res.data.length > 0) {
      setScopeId(String(res.data[0].id));
    } else {
      onError(`No SKU found matching '${skuLookup}'`);
    }
  };

  const submit = async () => {
    if (!scopeId || !deadlineDate) {
      onError("Scope and deadline date are required.");
      return;
    }
    setSubmitting(true);
    onError(null);
    try {
      await api.post("/deadlines", {
        scope_type: scopeType,
        scope_id: Number(scopeId),
        deadline_date: deadlineDate,
        warning_days: warningDays,
        notes,
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
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Scope Type</label>
          <select value={scopeType} onChange={(e) => setScopeType(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full">
            <option value="SKU">SKU</option>
            <option value="PRODUCT">Product</option>
            <option value="BRAND">Brand</option>
            <option value="CATEGORY">Category</option>
          </select>
        </div>
        {scopeType === "SKU" ? (
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">SKU</label>
            <div className="flex gap-1">
              <input value={skuLookup} onChange={(e) => setSkuLookup(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
              <button onClick={lookupSku} className="text-xs border border-slate-300 rounded px-2 hover:bg-slate-50">
                Find
              </button>
            </div>
          </div>
        ) : (
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">Scope ID</label>
            <input value={scopeId} onChange={(e) => setScopeId(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
          </div>
        )}
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Deadline Date</label>
          <input type="date" value={deadlineDate} onChange={(e) => setDeadlineDate(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Warning Days</label>
          <input type="number" value={warningDays} onChange={(e) => setWarningDays(Number(e.target.value))} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Notes</label>
          <input value={notes} onChange={(e) => setNotes(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full" />
        </div>
      </div>
      <button onClick={submit} disabled={submitting} className="mt-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded">
        {submitting ? "Saving…" : "Save Deadline"}
      </button>
    </div>
  );
}
