import React, { useState } from "react";
import { Card, Chip, ProgressBar, RiskBadge, SourceBadge, ErrorBanner, Spinner, Stat } from "../components/ui.jsx";
import { api } from "../services/api.js";

const DEMO_QUESTION =
  "What if I spend the next two days preparing for my Mathematics exam instead of completing my Physics assignment?";

const REASONS = [
  "The assignment deadline is more important to me",
  "I prefer another task first",
  "Deadline is less important to me",
  "I have more/less time than expected",
  "My priorities changed",
  "Other",
];

function ScenarioCard({ scenario, tone }) {
  const accent = tone === "a" ? "border-twin-500/30" : "border-violet-500/30";
  const p = scenario.deadline_pressure;
  return (
    <div className={`card ${accent} flex flex-col`}>
      <header className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="label">Scenario {scenario.key}</p>
          <h3 className="text-base font-semibold text-slate-100">{scenario.title}</h3>
        </div>
        <RiskBadge level={p.level} />
      </header>
      <p className="text-xs text-slate-400">{scenario.description}</p>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <Stat label="Study time used" value={`${scenario.total_allocated.toFixed(1)} h`} sub="estimate" tone="blue" />
        <Stat
          label="Tasks fully done"
          value={scenario.tasks_completed.length}
          sub={`${scenario.tasks_delayed.length} still open`}
          tone={scenario.tasks_completed.length ? "green" : "slate"}
        />
      </div>

      <div className="mt-4">
        <p className="label mb-2">Time allocation (estimated)</p>
        <div className="space-y-2">
          {scenario.time_allocation.map((a) => (
            <div key={a.title}>
              <div className="flex items-center justify-between text-xs text-slate-300">
                <span>{a.title}</span>
                <span className="text-slate-500">{a.hours.toFixed(1)} h</span>
              </div>
              <ProgressBar value={a.percent_of_capacity} height={6} />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4">
        <p className="label mb-2">Expected progress</p>
        <ul className="space-y-2">
          {scenario.task_outcomes.map((t) => (
            <li key={t.id} className="rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-slate-200">{t.title}</span>
                <Chip tone={t.status === "On track" ? "green" : t.status === "At risk" ? "amber" : "rose"}>
                  {t.status}
                </Chip>
              </div>
              <div className="mt-1.5">
                <ProgressBar
                  value={t.progress_after}
                  tone={t.status === "On track" ? "green" : t.status === "At risk" ? "amber" : "rose"}
                  height={5}
                />
              </div>
              <p className="mt-1 text-[11px] text-slate-500">
                {t.progress_before}% → {t.progress_after}% (est.) · {t.remaining_hours.toFixed(1)} h left
              </p>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="label mb-2 text-emerald-300">Benefits</p>
          <ul className="space-y-1.5 text-[11px] text-slate-300">
            {scenario.benefits.map((b, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-emerald-400">+</span>
                {b}
              </li>
            ))}
            {scenario.benefits.length === 0 && <li className="text-slate-500">No clear benefit identified.</li>}
          </ul>
        </div>
        <div>
          <p className="label mb-2 text-rose-300">Risks</p>
          <ul className="space-y-1.5 text-[11px] text-slate-300">
            {scenario.risks.map((r, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-rose-400">!</span>
                {r}
              </li>
            ))}
            {scenario.risks.length === 0 && <li className="text-slate-500">No significant risk identified.</li>}
          </ul>
        </div>
      </div>

      {scenario.conflicts.length > 0 && (
        <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2">
          <p className="label mb-1 text-amber-300">Potential conflicts</p>
          <ul className="space-y-1 text-[11px] text-amber-100/80">
            {scenario.conflicts.map((c, i) => (
              <li key={i}>• {c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function WhatIf({ onTwinChanged }) {
  const [question, setQuestion] = useState(DEMO_QUESTION);
  const [horizon, setHorizon] = useState(2);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showWhy, setShowWhy] = useState(false);
  const [feedbackState, setFeedbackState] = useState(null);
  const [reason, setReason] = useState(REASONS[0]);
  const [updateResult, setUpdateResult] = useState(null);
  const [previousPrimary, setPreviousPrimary] = useState(null);
  const [changed, setChanged] = useState(false);

  async function runSimulation() {
    if (!question.trim()) {
      setError("Please enter a What-If question.");
      return;
    }
    setLoading(true);
    setError("");
    setChanged(false);
    try {
      const data = await api.whatIf({ question: question.trim(), horizon_days: horizon });
      if (result?.recommendation?.primary_scenario) {
        setPreviousPrimary(result.recommendation.primary_scenario);
        setChanged(result.recommendation.primary_scenario !== data.recommendation.primary_scenario);
      }
      setResult(data);
      setFeedbackState(null);
      setUpdateResult(null);
      setShowWhy(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function sendFeedback(useful) {
    setFeedbackState({ useful, reason: useful ? null : reason });
  }

  async function submitFeedback() {
    if (!feedbackState) return;
    setLoading(true);
    setError("");
    try {
      const data = await api.feedback({
        question: result.question,
        recommendation_shown: result.recommendation.primary_scenario,
        useful: feedbackState.useful,
        reason: feedbackState.useful ? null : reason,
        chosen_scenario: result.recommendation.primary_scenario,
      });
      setUpdateResult(data);
      onTwinChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <Card title="WHAT IF?" subtitle="Simulate two futures from your stored data. Estimates are labelled as estimates — never presented as certainty.">
        <div className="flex flex-col gap-3 md:flex-row">
          <input
            className="input flex-1"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a What-If question…"
            onKeyDown={(e) => e.key === "Enter" && runSimulation()}
          />
          <select className="input md:w-40" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
            <option value={1}>1 day ahead</option>
            <option value={2}>2 days ahead</option>
            <option value={3}>3 days ahead</option>
          </select>
          <button className="btn-primary md:w-44" onClick={runSimulation} disabled={loading}>
            {loading ? "Simulating…" : "Run simulation"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {[DEMO_QUESTION, "What if I skip studying tonight?", "What if I study 2 extra hours tomorrow?"].map((q) => (
            <button
              key={q}
              className="chip border-white/10 bg-white/5 text-slate-400 hover:text-slate-200"
              onClick={() => setQuestion(q)}
            >
              {q.length > 62 ? q.slice(0, 62) + "…" : q}
            </button>
          ))}
        </div>
        <ErrorBanner message={error} onRetry={runSimulation} />
      </Card>

      {loading && !result && (
        <Card>
          <Spinner label="TwinEngine is simulating scenarios from your stored data…" />
        </Card>
      )}

      {result && (
        <>
          {changed && (
            <div className="animate-fade-up rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
              <span className="font-semibold">Recommendation changed.</span> It was Scenario {previousPrimary}, and is
              now Scenario {result.recommendation.primary_scenario} — because your feedback changed the twin's stored
              priority policy.
            </div>
          )}

          <Card title="Basis of this simulation" subtitle="Only permitted data was used">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Stat label="Horizon" value={`${result.horizon_days} days`} />
              <Stat
                label="Daily study capacity"
                value={`${result.assumptions.daily_capacity_hours.toFixed(1)} h`}
                sub="estimate from routine + history"
                tone="blue"
              />
              <Stat
                label="Total capacity"
                value={`${result.assumptions.total_capacity_hours.toFixed(1)} h`}
                sub="estimate"
                tone="blue"
              />
              <Stat
                label="Work remaining"
                value={`${result.assumptions.total_remaining_hours.toFixed(1)} h`}
                sub="from your tasks"
                tone="amber"
              />
            </div>
            <ul className="mt-2 space-y-1 text-[11px] text-slate-500">
              {result.assumptions.notes.map((n, i) => (
                <li key={i}>• {n}</li>
              ))}
            </ul>
            {result.missing_information?.length > 0 && (
              <div className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200/90">
                <span className="font-semibold">Missing information:</span> {result.missing_information.join("; ")}
              </div>
            )}
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            {result.scenarios.map((s, i) => (
              <ScenarioCard key={s.key} scenario={s} tone={i === 0 ? "a" : "b"} />
            ))}
          </div>

          <Card
            className="border-emerald-500/20 bg-gradient-to-br from-emerald-500/[0.07] to-ink-900/70"
            title="RECOMMENDATION"
            right={<SourceBadge source={result.recommendation.source} />}
          >
            <p className="text-sm leading-relaxed text-slate-200">{result.recommendation.text}</p>

            <div className="mt-3 flex flex-wrap gap-2">
              <Chip tone="green">Primary: Scenario {result.recommendation.primary_scenario}</Chip>
              <Chip tone="slate">Lower-risk option: Scenario {result.recommendation.lower_risk_scenario}</Chip>
              <Chip tone="amber">Not a guarantee — decision support only</Chip>
            </div>

            <button
              className="mt-4 text-xs font-semibold text-twin-400 underline decoration-dotted"
              onClick={() => setShowWhy((v) => !v)}
            >
              Why am I seeing this?
            </button>

            {showWhy && (
              <div className="mt-3 rounded-xl border border-white/10 bg-ink-950/50 p-4 animate-fade-up">
                <p className="label mb-2">Factors considered</p>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {result.explanation.factors.map((f, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="text-emerald-400">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                {result.explanation.not_used.length > 0 && (
                  <>
                    <p className="label mb-2 mt-4 text-amber-300">Not used (permission disabled)</p>
                    <ul className="space-y-1.5 text-xs text-amber-200/80">
                      {result.explanation.not_used.map((f, i) => (
                        <li key={i}>✗ {f}</li>
                      ))}
                    </ul>
                  </>
                )}
                <p className="mt-3 text-[11px] text-slate-500">{result.explanation.disclaimer}</p>
              </div>
            )}

            <div className="mt-5">
              <p className="label mb-2">Suggested balanced plan (estimate)</p>
              <div className="grid gap-3 md:grid-cols-2">
                {result.balanced_plan.map((day) => (
                  <div key={day.day} className="card-tight">
                    <p className="mb-2 text-xs font-semibold text-slate-200">{day.day}</p>
                    <ul className="space-y-1.5">
                      {day.blocks.map((b, i) => (
                        <li
                          key={i}
                          className={`flex items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-[11px] ${
                            b.type === "break" || b.type === "review"
                              ? "bg-white/[0.02] text-slate-500"
                              : "bg-twin-500/10 text-slate-200"
                          }`}
                        >
                          <span className="font-mono text-[10px] text-slate-400">
                            {b.start}–{b.end}
                          </span>
                          <span className="flex-1 text-right">{b.label}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card title="Was this recommendation useful?" subtitle="Your answer changes the Digital Twin">
            {!updateResult ? (
              <>
                <div className="flex flex-wrap gap-3">
                  <button
                    className={`btn ${
                      feedbackState?.useful === true
                        ? "bg-emerald-500 text-white"
                        : "border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                    }`}
                    onClick={() => sendFeedback(true)}
                  >
                    👍 Yes, this fits me
                  </button>
                  <button
                    className={`btn ${
                      feedbackState?.useful === false
                        ? "bg-rose-500 text-white"
                        : "border border-rose-500/30 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
                    }`}
                    onClick={() => sendFeedback(false)}
                  >
                    👎 No, I would choose differently
                  </button>
                </div>

                {feedbackState && (
                  <div className="mt-4 animate-fade-up space-y-3">
                    {feedbackState.useful === false && (
                      <div>
                        <p className="label mb-2">Why?</p>
                        <div className="flex flex-wrap gap-2">
                          {REASONS.map((r) => (
                            <button
                              key={r}
                              onClick={() => setReason(r)}
                              className={`chip ${
                                reason === r
                                  ? "border-twin-500/50 bg-twin-500/20 text-twin-400"
                                  : "border-white/10 bg-white/5 text-slate-400 hover:text-slate-200"
                              }`}
                            >
                              {r}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    <button className="btn-primary" onClick={submitFeedback} disabled={loading}>
                      {loading ? "Updating twin…" : "Submit feedback"}
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="animate-fade-up space-y-4">
                <div className="flex items-center gap-2 text-emerald-300">
                  <span className="text-lg">✓</span>
                  <span className="text-sm font-semibold">Twin Updated ✓</span>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="card-tight border-white/10">
                    <p className="label mb-1 text-slate-500">BEFORE FEEDBACK</p>
                    <p className="text-xs text-slate-400 line-through">{updateResult.update.before_text}</p>
                  </div>
                  <div className="card-tight border-emerald-500/30 bg-emerald-500/[0.07]">
                    <p className="label mb-1 text-emerald-300">AFTER FEEDBACK</p>
                    <p className="text-xs text-slate-200">{updateResult.update.after_text}</p>
                  </div>
                </div>

                <div className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3">
                  <p className="label mb-1">New learned preference</p>
                  <p className="text-sm text-slate-200">{updateResult.learned_preference.value === "deadline_first" ? "When an assignment deadline is within 48 hours, prioritize the assignment even when an exam is approaching." : "Prioritize upcoming exams over assignment deadlines."}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <SourceBadge source="learned" />
                    <Chip tone="blue">Understanding {updateResult.twin_confidence}%</Chip>
                    <Chip tone="slate">Stored as a preference record</Chip>
                  </div>
                </div>

                <button className="btn-ghost" onClick={runSimulation} disabled={loading}>
                  Ask the same question again →
                </button>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}