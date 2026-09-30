import React from "react";

export function Card({ title, subtitle, right, children, className = "", dense = false }) {
  return (
    <section className={`card animate-fade-up ${className}`}>
      {(title || right) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-sm font-semibold text-slate-100">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className={dense ? "" : "space-y-3"}>{children}</div>
    </section>
  );
}

const TONES = {
  slate: "border-white/10 bg-white/5 text-slate-300",
  blue: "border-twin-500/30 bg-twin-500/10 text-twin-400",
  green: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  amber: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  rose: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  violet: "border-violet-500/30 bg-violet-500/10 text-violet-300",
};

export function Chip({ children, tone = "slate", className = "" }) {
  return <span className={`chip ${TONES[tone] || TONES.slate} ${className}`}>{children}</span>;
}

export function RiskBadge({ level }) {
  const map = { Low: "green", Moderate: "amber", High: "rose" };
  return <Chip tone={map[level] || "slate"}>{level} risk</Chip>;
}

export function SourceBadge({ source }) {
  const map = {
    user: { tone: "blue", label: "User-provided" },
    inferred: { tone: "violet", label: "System-inferred" },
    predicted: { tone: "amber", label: "AI prediction" },
    learned: { tone: "green", label: "Learned from feedback" },
  };
  const cfg = map[source] || map.user;
  return <Chip tone={cfg.tone}>{cfg.label}</Chip>;
}

export function ProgressBar({ value = 0, tone = "blue", height = 8 }) {
  const colors = { blue: "bg-twin-500", green: "bg-emerald-500", amber: "bg-amber-500", rose: "bg-rose-500" };
  return (
    <div className="w-full overflow-hidden rounded-full bg-white/5" style={{ height }}>
      <div
        className={`h-full rounded-full transition-all duration-700 ${colors[tone] || colors.blue}`}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function EmptyState({ title, hint, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-white/10 px-6 py-10 text-center">
      <p className="text-sm font-medium text-slate-300">{title}</p>
      {hint && <p className="max-w-sm text-xs text-slate-500">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
      <span>{message}</span>
      {onRetry && (
        <button className="shrink-0 text-xs font-semibold underline" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Spinner({ label = "Thinking…" }) {
  return (
    <div className="flex items-center gap-3 text-xs text-slate-400">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-twin-500 border-t-transparent" />
      {label}
    </div>
  );
}

export function Stat({ label, value, sub, tone = "slate" }) {
  const colors = {
    slate: "text-slate-100",
    blue: "text-twin-400",
    green: "text-emerald-300",
    amber: "text-amber-300",
    rose: "text-rose-300",
    violet: "text-violet-300",
  };
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.03] px-4 py-3">
      <p className="label">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${colors[tone]}`}>{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-slate-500">{sub}</p>}
    </div>
  );
}