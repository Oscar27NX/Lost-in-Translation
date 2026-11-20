import React, { useState } from "react";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Edit3,
  Flag,
  History,
  RefreshCw,
  Save,
  X,
} from "lucide-react";
import {
  FLAG_CATEGORY_META,
  type FidelityMode,
  type FlagCategory,
  type InfoTreeDocument,
  type LineStatus,
  type ProofLine,
} from "../types";
import { MathBlock } from "./MathBlock";

interface LatexProofPaneProps {
  infotree: InfoTreeDocument;
  lines: ProofLine[];
  selectedLineId: string | null;
  hoveredLineId: string | null;
  editingLineId: string | null;
  flaggingLineId: string | null;
  regenLineId: string | null;
  busyLineId: string | null;
  onSelectLine: (lineId: string) => void;
  onHoverLine: (lineId: string | null) => void;
  onStartEdit: (lineId: string | null) => void;
  onStartFlag: (lineId: string | null) => void;
  onStartRegen: (lineId: string | null) => void;
  onVerifyLine: (line: ProofLine) => Promise<void>;
  onSaveEdit: (lineId: string, newLatex: string) => Promise<void>;
  onSubmitFlag: (lineId: string, cats: FlagCategory[], comment: string) => Promise<void>;
  onRegenerateLine: (
    lineId: string,
    fidelity: FidelityMode,
    instruction: string,
    useActiveFlags: boolean
  ) => Promise<void>;
  scrollContainerRef: React.RefObject<HTMLDivElement>;
  registerLatexCardRef: (lineId: string, el: HTMLDivElement | null) => void;
  onScrollSync: () => void;
}

const STATUS_BADGE: Record<LineStatus, { label: string; cls: string }> = {
  unreviewed: { label: "Unreviewed", cls: "badge-unreviewed" },
  verified: { label: "Verified", cls: "badge-verified" },
  flagged: { label: "Flagged", cls: "badge-flagged" },
  edited: { label: "Human-Edited", cls: "badge-edited" },
};

export const LatexProofPane: React.FC<LatexProofPaneProps> = ({
  infotree,
  lines,
  selectedLineId,
  hoveredLineId,
  editingLineId,
  flaggingLineId,
  regenLineId,
  busyLineId,
  onSelectLine,
  onHoverLine,
  onStartEdit,
  onStartFlag,
  onStartRegen,
  onVerifyLine,
  onSaveEdit,
  onSubmitFlag,
  onRegenerateLine,
  scrollContainerRef,
  registerLatexCardRef,
  onScrollSync,
}) => {
  const [draftLatex, setDraftLatex] = useState("");
  const [flagCats, setFlagCats] = useState<FlagCategory[]>(["opaque_tactic_elision"]);
  const [flagComment, setFlagComment] = useState("");
  const [regenMode, setRegenMode] = useState<FidelityMode>("expanded");
  const [regenInstruction, setRegenInstruction] = useState("");
  const [regenUseFlags, setRegenUseFlags] = useState(true);

  const openInlineEdit = (line: ProofLine) => {
    setDraftLatex(line.latex);
    onStartFlag(null);
    onStartRegen(null);
    onStartEdit(line.line_id);
  };

  const openInlineFlag = (line: ProofLine) => {
    setFlagCats(
      line.derivation.opaque_automation ? ["opaque_tactic_elision"] : ["semantic_drift"]
    );
    setFlagComment("");
    onStartEdit(null);
    onStartRegen(null);
    onStartFlag(line.line_id);
  };

  const openInlineRegen = (line: ProofLine) => {
    setRegenMode(line.derivation.opaque_automation ? "expanded" : "literal");
    setRegenInstruction("");
    setRegenUseFlags(true);
    onStartEdit(null);
    onStartFlag(null);
    onStartRegen(line.line_id);
  };

  const toggleFlagCat = (cat: FlagCategory) => {
    setFlagCats((prev) =>
      prev.includes(cat) ? (prev.length > 1 ? prev.filter((c) => c !== cat) : prev) : [...prev, cat]
    );
  };

  return (
    <div className="pane pane-latex">
      <div className="pane-header">
        <div className="pane-title-group">
          <span className="pane-title">Step-by-step proof</span>
          <span className="pane-subtitle">
            {lines.length} aligned step{lines.length === 1 ? "" : "s"}
          </span>
        </div>
        <div className="pane-actions">
          <span className="kbd-hint">
            <kbd>j</kbd>/<kbd>k</kbd> nav · <kbd>v</kbd> verify · <kbd>f</kbd> flag · <kbd>e</kbd> edit · <kbd>r</kbd> regen
          </span>
        </div>
      </div>

      <div
        className="latex-scroll"
        ref={scrollContainerRef}
        onScroll={onScrollSync}
      >
        {/* Theorem Statement Card */}
        <div className="theorem-card">
          <div className="theorem-kicker">
            <span>Theorem</span>
            <code>{infotree.theorem_name}</code>
          </div>
          <div className="theorem-math">
            <MathBlock latex={infotree.statement_latex} displayMode />
          </div>
          <div className="theorem-lean-sub">{infotree.statement_lean}</div>
        </div>

        <div className="proof-begin-marker">Proof.</div>

        {lines.length === 0 ? (
          <div className="empty-filter-state">
            No proof lines match the current filter. Select <strong>All Steps</strong> above to view the full proof.
          </div>
        ) : (
          <div className="latex-line-list">
            {lines.map((line) => {
              const isSelected = line.line_id === selectedLineId;
              const isHovered = line.line_id === hoveredLineId;
              const isEditing = line.line_id === editingLineId;
              const isFlagging = line.line_id === flaggingLineId;
              const isRegenerating = line.line_id === regenLineId;
              const isBusy = line.line_id === busyLineId;
              const activeFlags = line.flags.filter((f) => !f.resolved);
              const badge = STATUS_BADGE[line.status];
              const isModifiedFromOriginal = line.latex.trim() !== line.original_latex.trim();

              return (
                <article
                  key={line.line_id}
                  ref={(el) => registerLatexCardRef(line.line_id, el as HTMLDivElement | null)}
                  style={{ marginLeft: `${line.indent_level * 16}px` }}
                  className={[
                    "proof-card",
                    `status-${line.status}`,
                    isSelected ? "is-selected" : "",
                    isHovered ? "is-hovered" : "",
                    line.derivation.opaque_automation ? "has-opaque" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onMouseEnter={() => onHoverLine(line.line_id)}
                  onMouseLeave={() => onHoverLine(null)}
                  onClick={() => onSelectLine(line.line_id)}
                >
                  {/* Card Top Provenance Row */}
                  <div className="proof-card-top">
                    <div className="proof-card-meta">
                      <span className="line-index-pill">Step {line.line_number}</span>
                      <span
                        className="span-pill"
                        title={`Output line ${line.line_number} derived from Lean lines ${line.lean_span.start_line}–${line.lean_span.end_line}`}
                      >
                        ← Lean L{line.lean_span.start_line}
                        {line.lean_span.end_line !== line.lean_span.start_line
                          ? `–L${line.lean_span.end_line}`
                          : ""}
                      </span>
                      <span className="section-label">{line.section_label}</span>
                    </div>

                    <div className="proof-card-badges">
                      {line.derivation.opaque_automation && (
                        <span
                          className="opaque-chip"
                          title="Relies on automated Lean tactic (linarith/omega/simp/norm_num) — inspect derivation"
                        >
                          <AlertTriangle size={11} /> Opaque tactic
                        </span>
                      )}
                      <span
                        className="conf-meter"
                        title={`Literal faithfulness confidence: ${Math.round(line.derivation.confidence * 100)}%`}
                      >
                        <span className="conf-track">
                          <span
                            className="conf-fill"
                            style={{ width: `${Math.round(line.derivation.confidence * 100)}%` }}
                          />
                        </span>
                        <span className="conf-num">
                          {Math.round(line.derivation.confidence * 100)}%
                        </span>
                      </span>
                      <span className={`status-badge ${badge.cls}`}>{badge.label}</span>
                    </div>
                  </div>

                  {/* Card Body: Either Rendered KaTeX or Live Inline Editor */}
                  {isEditing ? (
                    <div
                      className="inline-editor"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="inline-editor-grid">
                        <div className="inline-editor-col">
                          <label className="inline-label">Raw LaTeX (edits captured for HITL DPO dataset)</label>
                          <textarea
                            className="latex-textarea"
                            rows={4}
                            value={draftLatex}
                            onChange={(e) => setDraftLatex(e.target.value)}
                            autoFocus
                          />
                        </div>
                        <div className="inline-editor-col">
                          <label className="inline-label">Live KaTeX Preview</label>
                          <div className="live-preview-box">
                            <MathBlock latex={draftLatex} />
                          </div>
                        </div>
                      </div>
                      <div className="inline-editor-actions">
                        <button
                          type="button"
                          className="btn-xs btn-primary"
                          disabled={isBusy}
                          onClick={() => onSaveEdit(line.line_id, draftLatex)}
                        >
                          <Save size={12} /> Save Human Edit
                        </button>
                        <button
                          type="button"
                          className="btn-xs btn-ghost"
                          onClick={() => setDraftLatex(line.original_latex)}
                          title="Reset editor text to initial LM inference"
                        >
                          Reset to Original
                        </button>
                        <button
                          type="button"
                          className="btn-xs btn-ghost"
                          onClick={() => onStartEdit(null)}
                        >
                          <X size={12} /> Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="proof-math-body">
                      <MathBlock latex={line.latex} />
                    </div>
                  )}

                  {/* Active Flag Banners */}
                  {activeFlags.length > 0 && (
                    <div className="flag-callout-list">
                      {activeFlags.map((fl) => (
                        <div key={fl.id} className="flag-callout">
                          <Flag size={13} className="flag-callout-icon" />
                          <div className="flag-callout-body">
                            <div className="flag-cat-row">
                              {fl.categories.map((cat) => (
                                <span key={cat} className="flag-cat-chip">
                                  {FLAG_CATEGORY_META[cat]?.label ?? cat}
                                </span>
                              ))}
                            </div>
                            {fl.comment && <p className="flag-comment-text">{fl.comment}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Quick Inline Flag Form */}
                  {isFlagging && (
                    <div
                      className="inline-popover flag-popover"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="popover-title">
                        <Flag size={13} /> Flag Faithfulness Defect on Step {line.line_number}
                      </div>
                      <div className="flag-pill-grid">
                        {(Object.keys(FLAG_CATEGORY_META) as FlagCategory[]).map((cat) => (
                          <button
                            key={cat}
                            type="button"
                            className={`cat-toggle ${flagCats.includes(cat) ? "is-picked" : ""}`}
                            onClick={() => toggleFlagCat(cat)}
                            title={FLAG_CATEGORY_META[cat].description}
                          >
                            {FLAG_CATEGORY_META[cat].label}
                          </button>
                        ))}
                      </div>
                      <input
                        type="text"
                        className="text-input"
                        placeholder="Describe what was lost or misstated (feeds targeted regeneration & DPO dataset)..."
                        value={flagComment}
                        onChange={(e) => setFlagComment(e.target.value)}
                      />
                      <div className="popover-actions">
                        <button
                          type="button"
                          className="btn-xs btn-danger"
                          disabled={isBusy}
                          onClick={() => onSubmitFlag(line.line_id, flagCats, flagComment)}
                        >
                          <Flag size={12} /> Record Flag
                        </button>
                        <button
                          type="button"
                          className="btn-xs btn-ghost"
                          onClick={() => onStartFlag(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Quick Inline Targeted Regeneration Form */}
                  {isRegenerating && (
                    <div
                      className="inline-popover regen-popover"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="popover-title">
                        <RefreshCw size={13} /> Targeted Single-Line Regeneration (Step {line.line_number} ← L{line.lean_span.start_line}–L{line.lean_span.end_line})
                      </div>
                      <div className="regen-controls-row">
                        <label className="inline-field">
                          <span>Fidelity Mode</span>
                          <select
                            className="select-xs"
                            value={regenMode}
                            onChange={(e) => setRegenMode(e.target.value as FidelityMode)}
                          >
                            <option value="literal">Literal (Formal Symbolic)</option>
                            <option value="expanded">Expanded Automation (Unpack tactics)</option>
                            <option value="formal_prose">Structured Mathematical Prose</option>
                          </select>
                        </label>
                        {activeFlags.length > 0 && (
                          <label className="checkbox-field">
                            <input
                              type="checkbox"
                              checked={regenUseFlags}
                              onChange={(e) => setRegenUseFlags(e.target.checked)}
                            />
                            <span>Inject {activeFlags.length} active flag critique(s)</span>
                          </label>
                        )}
                      </div>
                      <input
                        type="text"
                        className="text-input"
                        placeholder="Optional directive (e.g., 'Keep exact Lean q.num notation', 'Unpack linarith step')..."
                        value={regenInstruction}
                        onChange={(e) => setRegenInstruction(e.target.value)}
                      />
                      <div className="popover-actions">
                        <button
                          type="button"
                          className="btn-xs btn-primary"
                          disabled={isBusy}
                          onClick={() =>
                            onRegenerateLine(
                              line.line_id,
                              regenMode,
                              regenInstruction,
                              regenUseFlags
                            )
                          }
                        >
                          <RefreshCw size={12} className={isBusy ? "spin" : ""} />
                          {isBusy ? "Regenerating…" : "Regenerate Step " + line.line_number}
                        </button>
                        <button
                          type="button"
                          className="btn-xs btn-ghost"
                          onClick={() => onStartRegen(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Derivation Summary + Prominent HITL Action Row */}
                  <div className="proof-card-footer">
                    <div className="derivation-teaser" title={line.derivation.justification}>
                      <span className="teaser-label">Derivation:</span>{" "}
                      <span className="teaser-text">{line.derivation.justification}</span>
                    </div>

                    <div
                      className="hitl-action-bar"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {line.revisions.length > 1 && (
                        <span
                          className="rev-badge"
                          title={`${line.revisions.length} revisions recorded${isModifiedFromOriginal ? " (differs from initial LM output)" : ""}`}
                        >
                          <History size={11} /> v{line.revisions.length}
                        </span>
                      )}
                      <button
                        type="button"
                        className={`hitl-btn hitl-verify ${line.status === "verified" ? "is-active" : ""}`}
                        disabled={isBusy}
                        onClick={() => onVerifyLine(line)}
                        title="Mark line as faithful & verified (v)"
                      >
                        {line.status === "verified" ? <CheckCircle2 size={13} /> : <Check size={13} />}
                        <span>{line.status === "verified" ? "Verified" : "Verify"}</span>
                      </button>
                      <button
                        type="button"
                        className={`hitl-btn hitl-flag ${line.status === "flagged" || isFlagging ? "is-active" : ""}`}
                        disabled={isBusy}
                        onClick={() => openInlineFlag(line)}
                        title="Flag translation defect (f)"
                      >
                        <Flag size={13} />
                        <span>Flag</span>
                      </button>
                      <button
                        type="button"
                        className={`hitl-btn hitl-edit ${isEditing ? "is-active" : ""}`}
                        disabled={isBusy}
                        onClick={() => openInlineEdit(line)}
                        title="Edit LaTeX directly with live preview (e)"
                      >
                        <Edit3 size={13} />
                        <span>Edit</span>
                      </button>
                      <button
                        type="button"
                        className={`hitl-btn hitl-regen ${isRegenerating ? "is-active" : ""}`}
                        disabled={isBusy}
                        onClick={() => openInlineRegen(line)}
                        title="Regenerate only this line (r)"
                      >
                        <RefreshCw size={13} className={isBusy ? "spin" : ""} />
                        <span>Regen</span>
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}

        <div className="proof-end-marker">□</div>
      </div>
    </div>
  );
};
