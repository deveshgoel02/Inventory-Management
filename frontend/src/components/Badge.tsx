import clsx from "clsx";

const COLOR_MAP: Record<string, string> = {
  // Movement classification
  FAST_MOVING: "bg-emerald-100 text-emerald-800",
  HEALTHY: "bg-sky-100 text-sky-800",
  SLOW_MOVING: "bg-amber-100 text-amber-800",
  VERY_SLOW: "bg-orange-100 text-orange-800",
  DEAD_STOCK: "bg-red-100 text-red-800",
  NEW_INSUFFICIENT_DATA: "bg-slate-100 text-slate-600",
  // Confidence / risk
  HIGH: "bg-emerald-100 text-emerald-800",
  MEDIUM: "bg-amber-100 text-amber-800",
  LOW: "bg-slate-100 text-slate-600",
  // Deadline status
  NORMAL: "bg-emerald-100 text-emerald-800",
  APPROACHING_DEADLINE: "bg-amber-100 text-amber-800",
  DUE: "bg-orange-100 text-orange-800",
  OVERDUE: "bg-red-100 text-red-800",
  RESOLVED: "bg-slate-100 text-slate-600",
  // Alert severity
  INFO: "bg-sky-100 text-sky-800",
  WARNING: "bg-amber-100 text-amber-800",
  CRITICAL: "bg-red-100 text-red-800",
  OPEN: "bg-amber-100 text-amber-800",
  ACKNOWLEDGED: "bg-sky-100 text-sky-800",
  // PO / import status
  DRAFT: "bg-slate-100 text-slate-600",
  SENT: "bg-sky-100 text-sky-800",
  PARTIALLY_RECEIVED: "bg-amber-100 text-amber-800",
  RECEIVED: "bg-emerald-100 text-emerald-800",
  CANCELLED: "bg-red-100 text-red-800",
  VALIDATED: "bg-sky-100 text-sky-800",
  IMPORTED: "bg-emerald-100 text-emerald-800",
  FAILED: "bg-red-100 text-red-800",
  PENDING: "bg-amber-100 text-amber-800",
  IN_PROGRESS: "bg-sky-100 text-sky-800",
  FULFILLED: "bg-emerald-100 text-emerald-800",
  ACCEPTED: "bg-emerald-100 text-emerald-800",
  DISMISSED: "bg-slate-100 text-slate-600",
};

export default function Badge({ label }: { label: string }) {
  const cls = COLOR_MAP[label] ?? "bg-slate-100 text-slate-700";
  return (
    <span className={clsx("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap", cls)}>
      {label.replace(/_/g, " ")}
    </span>
  );
}
