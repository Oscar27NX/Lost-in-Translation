import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, Edit3, Flag, Filter } from "lucide-react";
import type { ProofLine, SessionMetrics } from "../types";

export type FilterMode =
  | "all"
  | "flagged"
  | "opaque"
  | "unreviewed"
  | "edited"
  | "verified";

interface ProofOverviewBarProps {
  lines: ProofLine[];
  metrics: SessionMetrics;
  filterMode: FilterMode;
  onFilterChange: (mode: FilterMode) => void;
  onGoToStep: (stepNumber: number) => void;
}

export const ProofOverviewBar: React.FC<ProofOverviewBarProps> = ({
  lines,
  metrics,
  filterMode,
  onFilterChange,
  onGoToStep,
}) => {
  const [stepInput, setStepInput] = useState("");
  const total = Math.max(metrics.total_lines, 1);
  const pct = (n: number) => `${Math.round((n / total) * 100)}%`;

  const filterButtons: { id: FilterMode; label: string; count: number; tone?: string }[] = [
    { id: "all", label: "All Steps", count: metrics.total_lines },
    { id: "flagged", label: "Flagged", count: metrics.flagged_count, tone: "danger" },
    { id: "opaque", label: "Opaque Tactics", count: metrics.opaque_tactic_count, tone: "warn" },
    { id: "unreviewed", label: "Unreviewed", count: metrics.unreviewed_count },
    { id: "edited", label: "Edited", count: metrics.edited_count, tone: "indigo" },
    { id: "verified", label: "Verified", count: metrics.verified_count, tone: "emerald" },
  ];

  const handleGoSubmit = (ev: React.FormEvent) => {
    ev.preventDefault();
    const trimmed = stepInput.trim();
    if (!/^-?\d+$/.test(trimmed)) return;
    const n = Number.parseInt(trimmed, 10);
    if (Number.isNaN(n) || n < 1 || lines.length === 0) return;
    const clamped = Math.min(n, lines.length);
    setStepInput(String(clamped));
    onGoToStep(clamped);
  };

  return (
    <section className="overview-bar" aria-label="Proof Verification Overview">
      <div className="overview-left">
        <div className="overview-metric-group">
          <div className="metric-block">
            <span className="metric-label">Audit Progress</span>
            <div className="progress-segmented" title="Click segments to filter by status">
              {metrics.verified_count > 0 && (
                <button
                  className="seg seg-verified"
                  style={{ width: pct(metrics.verified_count) }}
                  onClick={() => onFilterChange("verified")}
                  title={`${metrics.verified_count} Verified`}
                />
              )}
              {metrics.edited_count > 0 && (
                <button
                  className="seg seg-edited"
                  style={{ width: pct(metrics.edited_count) }}
                  onClick={() => onFilterChange("edited")}
                  title={`${metrics.edited_count} Human-Edited`}
                />
              )}
              {metrics.unreviewed_count > 0 && (
                <button
                  className="seg seg-unreviewed"
                  style={{ width: pct(metrics.unreviewed_count) }}
                  onClick={() => onFilterChange("unreviewed")}
                  title={`${metrics.unreviewed_count} Unreviewed`}
                />
              )}
              {metrics.flagged_count > 0 && (
                <button
                  className="seg seg-flagged"
                  style={{ width: pct(metrics.flagged_count) }}
                  onClick={() => onFilterChange("flagged")}
                  title={`${metrics.flagged_count} Flagged`}
                />
              )}
            </div>
            <div className="progress-legend">
              <span className="leg-item leg-verified">
                <CheckCircle2 size={11} /> {metrics.verified_count} verified
              </span>
              <span className="leg-item leg-edited">
                <Edit3 size={11} /> {metrics.edited_count} edited
              </span>
              <span className="leg-item leg-flagged">
                <Flag size={11} /> {metrics.flagged_count} flagged
              </span>
              <span className="leg-item leg-opaque">
                <AlertTriangle size={11} /> {metrics.opaque_tactic_count} opaque
              </span>
            </div>
          </div>

          <div className="metric-kpi">
            <span className="kpi-value">{Math.round(metrics.lean_line_coverage * 100)}%</span>
            <span className="kpi-label">Lean Coverage</span>
          </div>

          <div className="metric-kpi">
            <span className="kpi-value">{Math.round(metrics.mean_confidence * 100)}%</span>
            <span className="kpi-label">Mean Fidelity</span>
          </div>
        </div>
      </div>

      <div className="overview-filters">
        <Filter size={13} className="filter-icon" />
        {filterButtons.map((btn) => (
          <button
            key={btn.id}
            type="button"
            className={`filter-pill ${filterMode === btn.id ? "is-active" : ""} ${btn.tone ? `tone-${btn.tone}` : ""}`}
            onClick={() => onFilterChange(btn.id)}
          >
            <span>{btn.label}</span>
            <span className="filter-count">{btn.count}</span>
          </button>
        ))}

        <form className="goto-step-form" onSubmit={handleGoSubmit}>
          <label htmlFor="goto-step-input" className="goto-step-label">
            Go to Step:
          </label>
          <input
            id="goto-step-input"
            type="text"
            inputMode="numeric"
            className="goto-step-input"
            value={stepInput}
            onChange={(e) => setStepInput(e.target.value)}
            placeholder={`1–${lines.length}`}
            aria-label="Go to step number"
          />
        </form>
      </div>
    </section>
  );
};
