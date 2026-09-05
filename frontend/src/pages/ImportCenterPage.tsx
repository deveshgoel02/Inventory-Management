import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../api/client";
import type { ImportJob } from "../api/types";
import PageHeader from "../components/PageHeader";
import Badge from "../components/Badge";
import { formatDateTime } from "../lib/format";

const TARGET_LABELS: Record<string, string> = {
  SALES: "Sales",
  PURCHASES: "Purchases",
  OPENING_STOCK: "Opening Stock",
  PRODUCTS: "Products / SKUs",
};

interface MappingSuggestion {
  header: string | null;
  confidence: string;
  required: boolean;
}

interface UploadResult {
  job_id: number;
  filename: string;
  total_rows: number;
  headers: string[];
  target_entity: string;
  target_entity_auto_detected: boolean;
  suggested_mapping: Record<string, MappingSuggestion>;
  status: string;
}

interface ValidationResult {
  job_id: number;
  status: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  issues: { row_issues: { row_index: number; errors: string[]; warnings: string[] }[] };
}

export default function ImportCenterPage() {
  const [file, setFile] = useState<File | null>(null);
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [mapping, setMapping] = useState<Record<string, string | null>>({});
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [committed, setCommitted] = useState<{ status: string; valid_rows: number; invalid_rows: number } | null>(null);
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadJobs = () => api.get<ImportJob[]>("/imports/jobs").then((r) => setJobs(r.data));

  useEffect(() => {
    loadJobs();
  }, []);

  const reset = () => {
    setUpload(null);
    setMapping({});
    setValidation(null);
    setCommitted(null);
    setFile(null);
    setError(null);
  };

  const doUpload = async () => {
    if (!file) {
      setError("Choose a file first — click \"Choose file\" above and pick a .csv or .xlsx, then Upload.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("target_entity", "AUTO");
      form.append("file", file);
      const res = await api.post<UploadResult>("/imports/jobs", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUpload(res.data);
      const initialMapping: Record<string, string | null> = {};
      Object.entries(res.data.suggested_mapping).forEach(([field, info]) => {
        initialMapping[field] = info.header;
      });
      setMapping(initialMapping);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  // Validate, then — only if every row is clean — import immediately with
  // no further click. A file with any error/duplicate always stops here so
  // the user can see and decide about it; a clean file just goes straight
  // through, matching "only stop and show me a screen if there's a problem."
  const doValidate = async () => {
    if (!upload) return;
    setBusy(true);
    setError(null);
    try {
      await api.post(`/imports/jobs/${upload.job_id}/mapping`, mapping);
      const res = await api.post<ValidationResult>(`/imports/jobs/${upload.job_id}/validate`);
      setValidation(res.data);
      if (res.data.invalid_rows === 0 && res.data.duplicate_rows === 0 && res.data.valid_rows > 0) {
        const commitRes = await api.post(`/imports/jobs/${upload.job_id}/commit`);
        setCommitted(commitRes.data);
        loadJobs();
      }
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const doCommit = async () => {
    if (!upload) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.post(`/imports/jobs/${upload.job_id}/commit`);
      setCommitted(res.data);
      loadJobs();
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader title="Import Center" description="Upload a sales or purchases sheet — the type and column mapping are detected automatically. A clean file imports immediately; anything with errors stops for you to review." />

      {error && <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</div>}

      {!upload && (
        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6">
          <div className="text-sm font-semibold text-slate-800 mb-3">Upload File</div>
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">File (.csv, .xlsx)</label>
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={(e) => {
                  setFile(e.target.files?.[0] ?? null);
                  setError(null);
                }}
                className="text-sm max-w-[70vw] text-slate-500 file:mr-3 file:cursor-pointer file:rounded file:border-0 file:bg-indigo-600 file:px-4 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-indigo-700"
              />
            </div>
            <button onClick={doUpload} disabled={busy} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded">
              {busy ? "Uploading…" : "Upload"}
            </button>
            {busy && (
              <span className="text-xs text-slate-400 self-end pb-2">
                First request after idle can take up to a minute while the server wakes up.
              </span>
            )}
          </div>
        </div>
      )}

      {upload && !validation && (
        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6">
          <div className="text-sm font-semibold text-slate-800 mb-1">
            Review Column Mapping ({upload.filename}, {upload.total_rows} rows)
          </div>
          <div className="text-xs text-slate-500 mb-3">
            Detected as{" "}
            <span className="font-medium text-slate-700">{TARGET_LABELS[upload.target_entity] ?? upload.target_entity}</span>
            {upload.target_entity_auto_detected ? " automatically from the file's columns." : "."} Not right? Edit the
            mapping below, or go back and re-upload.
          </div>
          <table className="w-full text-sm mb-3">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b border-slate-100">
                <th className="py-1.5">Field</th>
                <th className="py-1.5">Mapped Column</th>
                <th className="py-1.5">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(upload.suggested_mapping).map(([field, info]) => (
                <tr key={field} className="border-b border-slate-50">
                  <td className="py-1.5 font-medium">
                    {field.replace(/_/g, " ")}
                    {info.required && <span className="text-red-500"> *</span>}
                  </td>
                  <td className="py-1.5">
                    <select
                      value={mapping[field] ?? ""}
                      onChange={(e) => setMapping({ ...mapping, [field]: e.target.value || null })}
                      className="border border-slate-300 rounded px-2 py-1 text-sm"
                    >
                      <option value="">— not mapped —</option>
                      {upload.headers.map((h) => (
                        <option key={h} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="py-1.5">
                    <Badge label={info.confidence} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex gap-2">
            <button onClick={doValidate} disabled={busy} className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded">
              {busy ? "Validating…" : "Validate"}
            </button>
            <button onClick={reset} className="text-sm border border-slate-300 rounded px-3 py-1.5 hover:bg-slate-50">
              Start Over
            </button>
          </div>
        </div>
      )}

      {validation && !committed && (
        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6">
          <div className="text-sm font-semibold text-slate-800 mb-3">Validation Report</div>
          <div className="grid grid-cols-4 gap-3 mb-4">
            <div className="bg-slate-50 rounded p-2 text-center">
              <div className="text-xs text-slate-500">Total Rows</div>
              <div className="text-lg font-semibold">{validation.total_rows}</div>
            </div>
            <div className="bg-emerald-50 rounded p-2 text-center">
              <div className="text-xs text-slate-500">Valid</div>
              <div className="text-lg font-semibold text-emerald-700">{validation.valid_rows}</div>
            </div>
            <div className="bg-red-50 rounded p-2 text-center">
              <div className="text-xs text-slate-500">Invalid</div>
              <div className="text-lg font-semibold text-red-700">{validation.invalid_rows}</div>
            </div>
            <div className="bg-amber-50 rounded p-2 text-center">
              <div className="text-xs text-slate-500">Duplicates</div>
              <div className="text-lg font-semibold text-amber-700">{validation.duplicate_rows}</div>
            </div>
          </div>
          {validation.issues.row_issues.length > 0 && (
            <div className="max-h-64 overflow-y-auto border border-slate-100 rounded mb-4">
              <table className="w-full text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="py-1.5 px-2 text-left">Row</th>
                    <th className="py-1.5 px-2 text-left">Errors</th>
                    <th className="py-1.5 px-2 text-left">Warnings</th>
                  </tr>
                </thead>
                <tbody>
                  {validation.issues.row_issues.map((ri) => (
                    <tr key={ri.row_index} className="border-t border-slate-100">
                      <td className="py-1 px-2">{ri.row_index + 1}</td>
                      <td className="py-1 px-2 text-red-600">{ri.errors.join("; ")}</td>
                      <td className="py-1 px-2 text-amber-600">{ri.warnings.join("; ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="flex gap-2">
            <button
              onClick={doCommit}
              disabled={busy || validation.valid_rows === 0}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm px-4 py-1.5 rounded"
            >
              {busy ? "Importing…" : `Confirm & Import ${validation.valid_rows} Valid Row(s)`}
            </button>
            <button onClick={reset} className="text-sm border border-slate-300 rounded px-3 py-1.5 hover:bg-slate-50">
              Start Over
            </button>
          </div>
        </div>
      )}

      {committed && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-6">
          <div className="text-sm font-semibold text-emerald-800 mb-1">Import Complete</div>
          <div className="text-sm text-emerald-700">
            {committed.valid_rows} row(s) imported, {committed.invalid_rows} row(s) skipped.
          </div>
          <button onClick={reset} className="mt-2 text-sm border border-emerald-300 rounded px-3 py-1.5 hover:bg-emerald-100">
            Import Another File
          </button>
        </div>
      )}

      <div className="text-sm font-semibold text-slate-800 mb-2">Recent Import Jobs</div>
      <div className="bg-white rounded-lg border border-slate-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-100 bg-slate-50">
              <th className="py-2 px-3">File</th>
              <th className="py-2 px-3">Target</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3 text-right">Valid / Invalid</th>
              <th className="py-2 px-3">Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} className="border-b border-slate-50">
                <td className="py-2 px-3">{j.filename}</td>
                <td className="py-2 px-3">{j.target_entity}</td>
                <td className="py-2 px-3">
                  <Badge label={j.status} />
                </td>
                <td className="py-2 px-3 text-right">
                  {j.valid_rows ?? "—"} / {j.invalid_rows ?? "—"}
                </td>
                <td className="py-2 px-3">{formatDateTime(j.uploaded_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
