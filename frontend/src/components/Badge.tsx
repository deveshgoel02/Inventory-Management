import clsx from "clsx";

const COLOR_MAP: Record<string, string> = {
  // Movement classification
  FAST_MOVING: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  HEALTHY: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  SLOW_MOVING: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  VERY_SLOW: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300",
  DEAD_STOCK: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  NEW_INSUFFICIENT_DATA: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  // Confidence / risk
  HIGH: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  MEDIUM: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  LOW: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  // Deadline status
  NORMAL: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  APPROACHING_DEADLINE: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  DUE: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300",
  OVERDUE: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  RESOLVED: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  // Alert severity
  INFO: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  WARNING: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  CRITICAL: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  OPEN: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  ACKNOWLEDGED: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  // PO / import status
  DRAFT: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  SENT: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  PARTIALLY_RECEIVED: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  RECEIVED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  CANCELLED: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  VALIDATED: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  IMPORTED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  FAILED: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  IN_PROGRESS: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  FULFILLED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  ACCEPTED: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  DISMISSED: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
};

export default function Badge({ label }: { label: string }) {
  const cls = COLOR_MAP[label] ?? "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300";
  return (
    <span className={clsx("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap", cls)}>
      {label.replace(/_/g, " ")}
    </span>
  );
}
