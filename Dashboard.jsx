import React, { useMemo, useState } from "react";
import { Card, Chip, ProgressBar, SourceBadge, Stat, EmptyState } from "../components/ui.jsx";

function daysUntil(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  const now = new Date();
  return Math.ceil((d.setHours(23, 59, 59, 999) - now.getTime()) / 86400000);
}

export default function Dashboard({ twin, onLoadDemo, onAsk, busy }) {
  const [showContext, setShowContext] = useState(false);

  const counts = twin?.counts;
  const patterns = twin?.patterns || [];
  const tasks = twin?.tasks || [];
  const goals = twin?.goals || [];
  const routine = twin?.routine || [];
  const updates = twin?.recent_updates || [];
  const profile = twin?.profile;
  const context = twin?.context;

  const studyWindow = useMemo(() => routine.filter((r) => r.category === "study"), [routine]);
  const isEmpty = !counts || (counts.tasks === 0 && counts.goals === 0 && counts.preferences === 0);

  if (isEmpty) {
    return (
      <Card title="Your Digital Twin is empty" subtitle="Nothing is loaded yet.">
        <EmptyState
          title="Load the demo student to explore HumanTwin AI"
          hint="This loads a synthetic student named Arjun — goals, tasks, preferences and a study history. No external account required."
          action={
            <button className="btn-primary" onClick={onLoadDemo} disabled={busy}>
              Load Demo Student
            </button>
          }
        />
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <Card
        className="border-twin-500/20 bg-gradient-to-br from-twin-500/10 via-ink-900/70 to-ink-900/70"
        title={`Your Digital Twin currently understands ${counts.preferences} preferences, ${counts.goals} goals, ${counts.tasks} tasks and ${counts.patterns} behavioral patterns.`}
        subtitle={`Twin understanding level — ${profile?.twin_confidence ?? 0}% · controlled by you`}
        right={
          <button className="btn-ghost text-xs" onClick={() => setShowContext((v) => !v)}>
            {showContext ? "Hide" : "What does my twin know about me?"}
          </button>
        }
      >
        <ProgressBar value={profile?.twin_confidence ?? 0} height={10} />
        <p className="text-xs text-slate-400">
          Confidence grows as you add data and give feedback. It never grows from data you have not permitted.
        </p>

        {showContext && context && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="card-tight">
              <p className="label mb-2">Preferences (user-provided)</p>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {context.preferences?.map((p, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-twin-400">•</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
            <div className="card-tight">
              <p className="label mb-2">Routine (user-provided)</p>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {context.routine?.map((r, i) => (
                  <li key={i} className="flex justify-between gap-2">
                    <span>{r.label}</span>
                    <span className="text-slate-500">
                      {r.start_time}–{r.end_time}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="card-tight">
              <p className="label mb-2">Goals</p>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {context.goals?.map((g, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-emerald-400">•</span>
                    {g}
                  </li>
                ))}
              </ul>
            </div>
            <div className="card-tight">
              <p className="label mb-2">Behavioral patterns (system-inferred)</p>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {context.patterns?.map((p, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-violet-400">•</span>
                    {p}
                  </li>
                ))}
              </ul>
            </div>
            {context.missing?.length > 0 && (
              <div className="card-tight md:col-span-2 border-amber-500/20 bg-amber-500/5">
                <p className="label mb-1 text-amber-300">Not available to the twin</p>
                <p className="text-xs text-amber-200/80">
                  {context.missing.join(", ")} — disabled in Data Control. The twin will say so instead of guessing.
                </p>
              </div>
            )}
          </div>
        )}
      </Card>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Today's Context" subtitle="Derived from your routine and open tasks">
          <div className="grid grid-cols-2 gap-3">
            <Stat
              label="Study window"
              value={studyWindow.length ? `${studyWindow[0].start_time}–${studyWindow[0].end_time}` : "—"}
            />
            <Stat
              label="Realistic daily study"
              value={`${profile?.avg_weekday_study_hours ?? "—"} h`}
              sub="from your study history"
              tone="blue"
            />
            <Stat label="Open tasks" value={counts.tasks} tone="amber" />
            <Stat label="Active goals" value={counts.goals} tone="green" />
          </div>
          <div className="mt-1 rounded-xl border border-white/5 bg-white/[0.03] px-4 py-3 text-xs text-slate-400">
            Today's plan is generated when you ask the twin. Nothing is scheduled automatically.
          </div>
        </Card>

        <Card title="Current Goals" subtitle="User-provided">
          <ul className="space-y-2">
            {goals.map((g) => (
              <li key={g.id} className="flex items-center justify-between gap-2 text-sm text-slate-200">
                <span>{g.title}</span>
                <Chip tone={g.priority === "High" ? "rose" : g.priority === "Medium" ? "amber" : "slate"}>
                  {g.priority}
                </Chip>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Upcoming Deadlines" subtitle="Estimates based on stored task data">
          <ul className="space-y-3">
            {tasks.map((t) => {
              const d = daysUntil(t.deadline);
              return (
                <li key={t.id} className="space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-slate-200">{t.title}</span>
                    <span className="text-[11px] text-slate-400">
                      {d === null ? "no date" : d <= 0 ? "due today" : `in ${d} day${d === 1 ? "" : "s"}`}
                    </span>
                  </div>
                  <ProgressBar
                    value={t.progress}
                    tone={t.progress >= 70 ? "green" : t.progress >= 35 ? "amber" : "rose"}
                    height={6}
                  />
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span>
                      {t.progress}% done · ~{(t.estimated_hours * (1 - t.progress / 100)).toFixed(1)} h left (est.)
                    </span>
                    <Chip tone={t.category === "exam" ? "violet" : "blue"}>{t.category}</Chip>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <Card
          className="lg:col-span-2"
          title="Behavioral Insights"
          subtitle="Every insight is derived from your stored data — nothing is invented"
        >
          <ul className="space-y-3">
            {patterns.map((p) => (
              <li key={p.id} className="card-tight">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-medium text-slate-100">{p.title}</p>
                  <div className="flex items-center gap-2">
                    <SourceBadge source="inferred" />
                    <Chip tone="slate">{Math.round(p.confidence * 100)}% conf.</Chip>
                  </div>
                </div>
                <p className="mt-1.5 text-xs text-slate-400">{p.description}</p>
                <p className="mt-1.5 text-[11px] text-slate-500">
                  <span className="font-semibold text-slate-400">Evidence:</span> {p.evidence}
                </p>
              </li>
            ))}
            {patterns.length === 0 && (
              <EmptyState
                title="Not enough data for behavioral patterns yet"
                hint="The twin needs recorded study sessions and decisions before it will claim a pattern."
              />
            )}
          </ul>
        </Card>

        <Card title="Twin Learning Status" subtitle="What changed, and why">
          <div className="rounded-xl border border-white/5 bg-white/[0.03] px-4 py-3">
            <p className="label">Understanding level</p>
            <div className="mt-2">
              <ProgressBar value={profile?.twin_confidence ?? 0} />
            </div>
            <p className="mt-2 text-xs text-slate-400">
              {profile?.twin_confidence ?? 0}% — based on {counts.preferences} preferences, {counts.patterns} patterns and{" "}
              {counts.decisions} recorded decisions.
            </p>
          </div>

          <p className="label mt-4">Recent twin updates</p>
          {updates.length === 0 ? (
            <p className="text-xs text-slate-500">No updates yet. Give feedback on a recommendation to see the twin change.</p>
          ) : (
            <ul className="space-y-2">
              {updates.slice(0, 4).map((u) => (
                <li key={u.id} className="card-tight">
                  <p className="text-xs font-semibold text-emerald-300">{u.title}</p>
                  <p className="mt-1 text-[11px] text-slate-500 line-through">{u.before_text}</p>
                  <p className="mt-1 text-[11px] text-slate-300">{u.after_text}</p>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-4 space-y-2">
            <button className="btn-primary w-full" onClick={() => onAsk("What should I focus on today?")}>
              Ask Your Digital Twin
            </button>
            <button className="btn-ghost w-full text-xs" onClick={onLoadDemo} disabled={busy}>
              Reload demo data
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}