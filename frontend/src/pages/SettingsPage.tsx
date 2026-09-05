import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import type { Brand, Warehouse } from "../api/types";
import PageHeader from "../components/PageHeader";
import { useAuth } from "../state/AuthContext";

export default function SettingsPage() {
  const { hasPermission } = useAuth();
  const [settings, setSettings] = useState<Record<string, unknown>>({});
  const [brands, setBrands] = useState<Brand[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [newBrandName, setNewBrandName] = useState("");
  const [newBrandCode, setNewBrandCode] = useState("");
  const [newWarehouseName, setNewWarehouseName] = useState("");
  const [newWarehouseCode, setNewWarehouseCode] = useState("");

  const loadSettings = () => api.get("/settings").then((r) => setSettings(r.data));
  const loadBrands = () => api.get<Brand[]>("/brands").then((r) => setBrands(r.data));
  const loadWarehouses = () => api.get<Warehouse[]>("/warehouses").then((r) => setWarehouses(r.data));

  useEffect(() => {
    loadSettings();
    loadBrands();
    loadWarehouses();
  }, []);

  const canManage = hasPermission("settings:manage");

  const updateSetting = async (key: string, value: unknown) => {
    try {
      await api.put(`/settings/${key}`, { value });
      loadSettings();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  const addBrand = async () => {
    try {
      await api.post("/brands", { name: newBrandName, code: newBrandCode });
      setNewBrandName("");
      setNewBrandCode("");
      loadBrands();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  const addWarehouse = async () => {
    try {
      await api.post("/warehouses", { name: newWarehouseName, code: newWarehouseCode });
      setNewWarehouseName("");
      setNewWarehouseCode("");
      loadWarehouses();
    } catch (e) {
      setError(apiErrorMessage(e));
    }
  };

  return (
    <div>
      <PageHeader title="Settings" description="Business rules, brands, and warehouses — no code changes required to adjust any of this." />
      {error && <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="text-sm font-semibold text-slate-800 mb-3">Business Rules</div>
          <div className="space-y-3">
            {Object.entries(settings).map(([key, value]) => (
              <SettingRow key={key} settingKey={key} value={value} canEdit={canManage} onSave={updateSetting} />
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-sm font-semibold text-slate-800 mb-3">Brands</div>
            <ul className="text-sm mb-3 space-y-1">
              {brands.map((b) => (
                <li key={b.id} className="flex justify-between border-b border-slate-50 py-1">
                  <span>{b.name}</span>
                  <span className="text-slate-400">{b.code}</span>
                </li>
              ))}
            </ul>
            {canManage && (
              <div className="flex gap-2">
                <input placeholder="Name" value={newBrandName} onChange={(e) => setNewBrandName(e.target.value)} className="border border-slate-300 rounded px-2 py-1 text-sm w-full" />
                <input placeholder="Code" value={newBrandCode} onChange={(e) => setNewBrandCode(e.target.value)} className="border border-slate-300 rounded px-2 py-1 text-sm w-24" />
                <button onClick={addBrand} className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded">
                  Add
                </button>
              </div>
            )}
          </div>

          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-sm font-semibold text-slate-800 mb-3">Warehouses</div>
            <ul className="text-sm mb-3 space-y-1">
              {warehouses.map((w) => (
                <li key={w.id} className="flex justify-between border-b border-slate-50 py-1">
                  <span>{w.name}</span>
                  <span className="text-slate-400">{w.code}</span>
                </li>
              ))}
            </ul>
            {canManage && (
              <div className="flex gap-2">
                <input placeholder="Name" value={newWarehouseName} onChange={(e) => setNewWarehouseName(e.target.value)} className="border border-slate-300 rounded px-2 py-1 text-sm w-full" />
                <input placeholder="Code" value={newWarehouseCode} onChange={(e) => setNewWarehouseCode(e.target.value)} className="border border-slate-300 rounded px-2 py-1 text-sm w-24" />
                <button onClick={addWarehouse} className="text-xs bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded">
                  Add
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingRow({
  settingKey,
  value,
  canEdit,
  onSave,
}: {
  settingKey: string;
  value: unknown;
  canEdit: boolean;
  onSave: (key: string, value: unknown) => void;
}) {
  const [draft, setDraft] = useState(JSON.stringify(value));

  return (
    <div className="flex items-center justify-between gap-2">
      <div className="text-xs font-medium text-slate-600 w-1/2">{settingKey.replace(/_/g, " ")}</div>
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        disabled={!canEdit}
        className="border border-slate-300 rounded px-2 py-1 text-xs w-1/2 disabled:bg-slate-50"
      />
      {canEdit && (
        <button
          onClick={() => {
            try {
              onSave(settingKey, JSON.parse(draft));
            } catch {
              onSave(settingKey, draft);
            }
          }}
          className="text-xs text-indigo-600 hover:underline shrink-0"
        >
          Save
        </button>
      )}
    </div>
  );
}
