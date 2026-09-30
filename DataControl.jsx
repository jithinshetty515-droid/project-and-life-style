import React, { useState } from "react";
import { Card, Chip, ErrorBanner } from "../components/ui.jsx";
import { api } from "../services/api.js";

const CATEGORY_LABELS = {
  goals: "Goals",
  preferences: "Preferences",
  routine: "Routine",
  tasks: "Tasks",
  calendar: "Calendar",
  study_history: "Study History",
  decision_history: "Decision History",
  personal_notes: "Personal Notes",
};

export default function DataControl({ permissions, onChanged, onLoadDemo }) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function toggle(perm) {
    setBusy(perm.category);
    setError("");
    try {
      await api.updatePermission({ category: perm.category, enabled: !perm.enabled });
      await onChanged();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function deleteData(category) {
    setBusy(category);
    setError("");
    try {
      await api.deleteCategoryData(category);
      setMessage(`Deleted stored data for “${CATEGORY_LABELS[category] || category}”.`);
      await onChanged();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function resetTwin() {
    if (!confirm("Reset the Digital Twin? All stored data and learned preferences will be deleted.")) return;
    setBusy("reset");
    setError("");
    try {
      await api.resetTwin();
      setMessage("Digital Twin reset. All stored data has been deleted.");
      await onChanged();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-5">
      <Card
        title="Data Control"
        subtitle="You decide what your Digital Twin is allowed to use. Nothing is accessed automatically."
        right={<Chip tone="green">Controlled by you</Chip>}
      >
        <ErrorBanner message={error} />
        {message && (
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            {message}
          </div>
        )}

        <ul className="space-y-3">
          {(permissions || []).map((p) => (
            <li key={p.category} className="card-tight flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-medium ${p.enabled ? "text-slate-100" : "text-slate-500"}`}>
                    {CATEGORY_LABELS[p.category] || p.category}
                  </span>
                  <Chip tone={p.enabled ? "green" : "slate"}>{p.enabled ? "Enabled" : "Disabled"}</Chip>
                  {p.record_count !== undefined && <Chip tone="slate">{p.record_count} records</Chip>}
                </div>
                <p className="mt-1.5 text-[11px] text-slate-400">
                  <span className="font-semibold text-slate-500">Stored:</span> {p.description}
                </p>
                <p className="mt-0.5 text-[11px] text-slate-400">
                  <span className="font-semibold text-slate-500">Why the twin uses it:</span> {p.used_for}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button className="btn-ghost text-xs" onClick={() => toggle(p)} disabled={busy === p.category}>
                  {p.enabled ? "Disable" : "Enable"}
                </button>
                <button className="btn-danger text-xs" onClick={() => deleteData(p.category)} disabled={busy === p.category}>
                  Delete Data
                </button>
              </div>
            </li>
          ))}
        </ul>
      </Card>

      <Card title="Danger zone" subtitle="Irreversible actions on your Digital Twin">
        <div className="flex flex-wrap gap-3">
          <button className="btn-danger" onClick={resetTwin} disabled={busy === "reset"}>
            Reset Digital Twin
          </button>
          <button className="btn-ghost" onClick={onLoadDemo} disabled={busy === "reset"}>
            Load Demo Student
          </button>
        </div>
        <p className="text-[11px] text-slate-500">
          Resetting deletes all goals, tasks, routine, history, patterns, feedback and learned preferences.
        </p>
      </Card>

      <Card title="Privacy design" subtitle="How this MVP handles data">
        <ul className="space-y-2 text-xs text-slate-400">
          <li>• No external personal data is accessed. The demo uses synthetic data; anything else is entered by you.</li>
          <li>• Every AI call receives only the categories you have enabled — never the whole database.</li>
          <li>• The twin never makes decisions for you. It shows trade-offs and leaves the choice to you.</li>
          <li>• If a category is disabled, the twin says the information is missing instead of guessing.</li>
          <li>• API keys are read from environment variables and are never sent to the browser.</li>
        </ul>
      </Card>
    </div>
  );
}