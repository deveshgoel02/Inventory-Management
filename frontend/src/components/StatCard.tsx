interface StatCardProps {
  label: string;
  value: string;
  sublabel?: string;
  tone?: "default" | "warning" | "danger" | "success";
}

const TONE_CLASSES: Record<string, string> = {
  default: "text-slate-900 dark:text-white",
  warning: "text-amber-600 dark:text-amber-400",
  danger: "text-red-600 dark:text-red-400",
  success: "text-emerald-600 dark:text-emerald-400",
};

export default function StatCard({ label, value, sublabel, tone = "default" }: StatCardProps) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
      <div className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${TONE_CLASSES[tone]}`}>{value}</div>
      {sublabel && <div className="mt-1 text-xs text-slate-400 dark:text-slate-500">{sublabel}</div>}
    </div>
  );
}
