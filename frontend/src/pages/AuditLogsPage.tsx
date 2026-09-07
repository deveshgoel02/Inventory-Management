import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuditLogEntry } from "../api/types";
import PageHeader from "../components/PageHeader";
import { formatDateTime } from "../lib/format";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [entityType, setEntityType] = useState("");

  const load = () => {
    const params: Record<string, string> = {};
    if (entityType) params.entity_type = entityType;
    api.get<AuditLogEntry[]>("/audit-logs", { params }).then((r) => setLogs(r.data));
  };

  useEffect(load, [entityType]);

  return (
    <div>
      <PageHeader title="Audit Logs" description="Every important inventory, sales, and configuration change, with before/after state and who made it." />

      <div className="mb-4">
        <select value={entityType} onChange={(e) => setEntityType(e.target.value)} className="border border-slate-300 dark:border-slate-600 rounded px-3 py-1.5 text-sm">
          <option value="">All entity types</option>
          <option value="product_variant">Product Variant (SKU)</option>
          <option value="product">Product</option>
          <option value="sale">Sale</option>
          <option value="stock_deadline">Stock Deadline</option>
          <option value="business_setting">Business Setting</option>
          <option value="user">User</option>
        </select>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-700/60 bg-slate-50 dark:bg-slate-800/60">
              <th className="py-2 px-3">When</th>
              <th className="py-2 px-3">Action</th>
              <th className="py-2 px-3">Entity</th>
              <th className="py-2 px-3">Reason</th>
              <th className="py-2 px-3">Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-b border-slate-50 dark:border-slate-800 align-top">
                <td className="py-2 px-3 whitespace-nowrap">{formatDateTime(l.created_at)}</td>
                <td className="py-2 px-3 font-medium">{l.action}</td>
                <td className="py-2 px-3">
                  {l.entity_type} #{l.entity_id}
                </td>
                <td className="py-2 px-3 text-slate-500 dark:text-slate-400">{l.reason ?? "—"}</td>
                <td className="py-2 px-3 text-xs text-slate-500 dark:text-slate-400 max-w-md">
                  {l.before && (
                    <div>
                      <span className="text-slate-400 dark:text-slate-500">before:</span> {JSON.stringify(l.before)}
                    </div>
                  )}
                  {l.after && (
                    <div>
                      <span className="text-slate-400 dark:text-slate-500">after:</span> {JSON.stringify(l.after)}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
