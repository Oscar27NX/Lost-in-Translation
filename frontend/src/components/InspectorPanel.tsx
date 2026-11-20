import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  GitCompare,
  History,
  Info,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  X,
  XCircle,
} from "lucide-react";
import {
  FLAG_CATEGORY_META,
  type GoalState,
  type InfoTreeDocument,
  type InfoTreeNode,
  type ProofLine,
} from "../types";
import { MathBlock } from "./MathBlock";

interface InspectorPanelProps {
  infotree: InfoTreeDocument;
  line: ProofLine | null;
  busy: boolean;
  onClose: () => void;
  onRevertRevision: (lineId: string, revIdx: number) => Promise<void>;
  onResolveFlags: (lineId: string) => Promise<void>;
}

type InspectorTab = "derivation" | "infotree" | "history";

const GoalStateCard: React.FC<{ title: string; goals: GoalState[]; tone: "before" | "after" }> = ({
  title,
  goals,
  tone,
}) => {
  if (goals.length === 0) {
    return (
      <div className={`goal-card goal-${tone}`}>
        <div className="goal-card-head">{title}</div>
        <div className="goal-empty">No open goals (discharged)</div>
      </div>
    );
  }
  return (
    <div className={`goal-card goal-${tone}`}>
      <div className="goal-card-head">
        <span>{title}</span>
        <span className="goal-count">{goals.length} goal{goals.length > 1 ? "s" : ""}</span>
      </div>
      {goals.map((g, gi) => (
        <div key={gi} className="goal-block">
          {g.tag && <div className="goal-tag">case {g.tag}</div>}
          <div className="hyp-list">
            {g.hypotheses.length === 0 ? (
              <div className="hyp-empty">(empty local context)</div>
            ) : (
              g.hypotheses.map((h, hi) => (
                <div key={hi} className={`hyp-row hyp-${h.change}`}>
                  <span className="hyp-diff-mark">
                    {h.change === "added" ? "+" : h.change === "modified" ? "~" : " "}
                  </span>
                  <span className="hyp-name">{h.name}</span>
                  <span className="hyp-colon">:</span>
                  <span className="hyp-type">{h.type}</span>
                </div>
              ))
            )}
          </div>
          <div className="goal-target">
            <span className="turnstile">⊢</span>
            <span>{g.target}</span>
          </div>
        </div>
      ))}
    </div>
  );
};

export const InspectorPanel: React.FC<InspectorPanelProps> = ({
  infotree,
  line,
  busy,
  onClose,
  onRevertRevision,
  onResolveFlags,
}) => {
  const [tab, setTab] = useState<InspectorTab>("derivation");

  if (!line) {
    return (
      <aside className="inspector-panel">
        <div className="inspector-header">
          <h2 className="inspector-title">No step selected</h2>
          <button
            type="button"
            className="inspector-close-btn"
            onClick={onClose}
            aria-label="Close metadata panel"
            title="Close metadata panel (Esc)"
          >
            <X size={16} />
          </button>
        </div>
        <div className="inspector-empty">
          <Info size={20} />
          <p>Click any proof step to inspect its Lean 4 InfoTree state transition, derivation procedure, and revision audit trail.</p>
        </div>
      </aside>
    );
  }

  const matchedNodes: InfoTreeNode[] = line.infotree_node_ids
    .map((id) => infotree.nodes.find((n) => n.node_id === id))
    .filter((n): n is InfoTreeNode => Boolean(n));

  const leanSlice = infotree.source_code
    .split("\n")
    .slice(line.lean_span.start_line - 1, line.lean_span.end_line)
    .join("\n");

  const unresolvedFlags = line.flags.filter((f) => !f.resolved);

  return (
    <aside className="inspector-panel" aria-label="Step Metadata and InfoTree Inspector">
      <div className="inspector-header">
        <h2 className="inspector-title">
          Step {line.line_number}: {line.section_label}
        </h2>
        <div className="inspector-header-right">
          <div className="inspector-model-pill" title="Active inference source for this line">
            <Cpu size={12} />
            <span>{line.derivation.model_id}</span>
          </div>
          <button
            type="button"
            className="inspector-close-btn"
            onClick={onClose}
            aria-label="Close metadata panel"
            title="Close metadata panel (Esc)"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="inspector-tabs">
        <button
          type="button"
          className={`ins-tab ${tab === "derivation" ? "is-active" : ""}`}
          onClick={() => setTab("derivation")}
        >
          <ShieldCheck size={13} /> Derivation &amp; Audit
        </button>
        <button
          type="button"
          className={`ins-tab ${tab === "infotree" ? "is-active" : ""}`}
          onClick={() => setTab("infotree")}
        >
          <GitCompare size={13} /> InfoTree State ({matchedNodes.length})
        </button>
        <button
          type="button"
          className={`ins-tab ${tab === "history" ? "is-active" : ""}`}
          onClick={() => setTab("history")}
        >
          <History size={13} /> Revisions ({line.revisions.length})
        </button>
      </div>

      <div className="inspector-body">
        {tab === "derivation" && (
          <div className="ins-section-stack">
            {/* Mapping Summary Box */}
            <div className="ins-card">
              <div className="ins-card-label">
                Image Mapping: Lean L{line.lean_span.start_line}–L{line.lean_span.end_line} <ArrowRight size={11} /> LaTeX Step {line.line_number}
              </div>
              <pre className="ins-code-slice">{leanSlice}</pre>
            </div>

            {/* Justification */}
            <div className="ins-card">
              <div className="ins-card-label">Justification</div>
              <p className="ins-prose">{line.derivation.justification}</p>
            </div>

            {/* Derivation Procedure */}
            <div className="ins-card">
              <div className="ins-card-label">Derivation Procedure</div>
              <ol className="ins-procedure-list">
                {line.derivation.procedure.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </div>

            {/* Faithfulness Diagnostics */}
            <div className="ins-card">
              <div className="ins-card-label">Automated Faithfulness Checks</div>
              <div className="checks-list">
                {line.derivation.checks.map((chk, i) => (
                  <div key={i} className={`check-row check-${chk.status}`}>
                    {chk.status === "pass" ? (
                      <CheckCircle2 size={14} />
                    ) : chk.status === "warn" ? (
                      <AlertTriangle size={14} />
                    ) : (
                      <XCircle size={14} />
                    )}
                    <div>
                      <div className="check-name">{chk.name}</div>
                      <div className="check-detail">{chk.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Tactics & Referenced Mathlib Constants */}
            <div className="ins-card">
              <div className="ins-card-label">Tactics &amp; Referenced Lean Constants</div>
              <div className="chip-cloud">
                {line.derivation.tactics_used.map((t) => (
                  <span key={`t-${t}`} className="chip-tactic">
                    {t}
                  </span>
                ))}
                {line.derivation.referenced_lemmas.map((lm) => (
                  <span key={`l-${lm}`} className="chip-lemma">
                    {lm}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === "infotree" && (
          <div className="ins-section-stack">
            {matchedNodes.length === 0 ? (
              <div className="ins-card">
                <p className="ins-prose">No InfoTree nodes linked to this line.</p>
              </div>
            ) : (
              matchedNodes.map((node) => (
                <div key={node.node_id} className="infotree-node-box">
                  <div className="infotree-node-head">
                    <code>{node.node_id}</code>
                    <span className="infotree-kind">{node.tactic_kind}</span>
                    <span className="infotree-span">
                      L{node.span.start_line}–L{node.span.end_line}
                    </span>
                  </div>
                  <GoalStateCard
                    title="Goals Before Tactic"
                    goals={node.goals_before}
                    tone="before"
                  />
                  <div className="goal-arrow-divider">
                    <span>tactic transition ↓</span>
                  </div>
                  <GoalStateCard
                    title="Goals After Tactic"
                    goals={node.goals_after}
                    tone="after"
                  />
                </div>
              ))
            )}
          </div>
        )}

        {tab === "history" && (
          <div className="ins-section-stack">
            {unresolvedFlags.length > 0 && (
              <div className="ins-card ins-flags-card">
                <div className="ins-card-label-row">
                  <span className="ins-card-label">
                    <ShieldAlert size={13} /> Active Reviewer Flags ({unresolvedFlags.length})
                  </span>
                  <button
                    type="button"
                    className="btn-xs btn-ghost"
                    disabled={busy}
                    onClick={() => onResolveFlags(line.line_id)}
                  >
                    Resolve All
                  </button>
                </div>
                {unresolvedFlags.map((fl) => (
                  <div key={fl.id} className="ins-flag-item">
                    <div className="flag-cat-row">
                      {fl.categories.map((c) => (
                        <span key={c} className="flag-cat-chip">
                          {FLAG_CATEGORY_META[c]?.label ?? c}
                        </span>
                      ))}
                    </div>
                    {fl.comment && <p className="ins-prose">{fl.comment}</p>}
                  </div>
                ))}
              </div>
            )}

            <div className="ins-card">
              <div className="ins-card-label">Line Revision Lineage</div>
              <div className="revision-timeline">
                {[...line.revisions].reverse().map((rev) => {
                  const isCurrent = rev.latex === line.latex;
                  return (
                    <div
                      key={rev.revision_index}
                      className={`rev-card ${isCurrent ? "is-current" : ""}`}
                    >
                      <div className="rev-head">
                        <span className="rev-num">v{rev.revision_index + 1}</span>
                        <span className={`rev-src src-${rev.source}`}>
                          {rev.source.replace("_", " ")}
                        </span>
                        <span className="rev-mode">{rev.fidelity_mode}</span>
                        {!isCurrent && (
                          <button
                            type="button"
                            className="btn-xs btn-ghost"
                            disabled={busy}
                            onClick={() => onRevertRevision(line.line_id, rev.revision_index)}
                          >
                            <RotateCcw size={11} /> Restore
                          </button>
                        )}
                      </div>
                      <div className="rev-math-preview">
                        <MathBlock latex={rev.latex} />
                      </div>
                      {rev.instruction && (
                        <div className="rev-directive">Directive: “{rev.instruction}”</div>
                      )}
                      {rev.justification && (
                        <div className="rev-just">{rev.justification}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
