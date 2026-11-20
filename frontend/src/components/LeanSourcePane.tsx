import React, { useMemo, useState } from "react";
import { Code2, Play, RotateCcw, Sparkles } from "lucide-react";
import type { FidelityMode, InfoTreeDocument, ProofLine } from "../types";

interface LeanSourcePaneProps {
  infotree: InfoTreeDocument;
  lines: ProofLine[];
  selectedLineId: string | null;
  hoveredLineId: string | null;
  onSelectLine: (lineId: string) => void;
  onHoverLine: (lineId: string | null) => void;
  onRetranslate: (leanSource: string, fidelity: FidelityMode) => Promise<void>;
  scrollContainerRef: React.RefObject<HTMLDivElement>;
  registerLeanLineRef: (lineNum: number, el: HTMLDivElement | null) => void;
  onScrollSync: () => void;
}

const LEAN_KEYWORDS = new Set([
  "import",
  "open",
  "theorem",
  "lemma",
  "def",
  "noncomputable",
  "example",
  "by",
  "have",
  "let",
  "intro",
  "intros",
  "obtain",
  "rcases",
  "induction",
  "with",
  "calc",
  "rw",
  "simp",
  "exact",
  "apply",
  "refine",
  "by_contra",
  "push_neg",
  "linarith",
  "omega",
  "field_simp",
  "norm_num",
  "exact_mod_cast",
  "zify",
  "push_cast",
  "unfold",
  "sorry",
]);

const OPAQUE_TOKENS = new Set([
  "linarith",
  "omega",
  "simp",
  "field_simp",
  "norm_num",
  "exact_mod_cast",
  "sorry",
]);

function highlightLeanLine(text: string): React.ReactNode {
  const trimmed = text.trim();
  if (trimmed.startsWith("--") || trimmed.startsWith("/-")) {
    return <span className="tok-comment">{text}</span>;
  }
  const commentIdx = text.indexOf("--");
  const codePart = commentIdx >= 0 ? text.slice(0, commentIdx) : text;
  const commentPart = commentIdx >= 0 ? text.slice(commentIdx) : "";

  const tokens = codePart.split(/(\s+|[()[\]{}⟨⟩,:;:=]+)/g);
  return (
    <>
      {tokens.map((tok, i) => {
        if (!tok) return null;
        if (OPAQUE_TOKENS.has(tok)) {
          return (
            <span key={i} className="tok-opaque" title="Automated tactic (audit recommended)">
              {tok}
            </span>
          );
        }
        if (LEAN_KEYWORDS.has(tok)) {
          return (
            <span key={i} className="tok-kw">
              {tok}
            </span>
          );
        }
        if (/^[ℕℤℚℝ∀∃≤≥≠∣∧∨¬→↔∈∉∑]$/.test(tok)) {
          return (
            <span key={i} className="tok-sym">
              {tok}
            </span>
          );
        }
        return <React.Fragment key={i}>{tok}</React.Fragment>;
      })}
      {commentPart && <span className="tok-comment">{commentPart}</span>}
    </>
  );
}

export const LeanSourcePane: React.FC<LeanSourcePaneProps> = ({
  infotree,
  lines,
  selectedLineId,
  hoveredLineId,
  onSelectLine,
  onHoverLine,
  onRetranslate,
  scrollContainerRef,
  registerLeanLineRef,
  onScrollSync,
}) => {
  const [editMode, setEditMode] = useState(false);
  const [draftSource, setDraftSource] = useState(infotree.source_code);
  const [fidelity, setFidelity] = useState<FidelityMode>("literal");
  const [busy, setBusy] = useState(false);

  // Sync draft when user switches proofs
  React.useEffect(() => {
    setDraftSource(infotree.source_code);
    setEditMode(false);
  }, [infotree.source_code]);

  const sourceLines = useMemo(() => infotree.source_code.split("\n"), [infotree.source_code]);

  // Map each 1-based Lean line number -> list of ProofLines covering it
  const lineToProofLines = useMemo(() => {
    const map = new Map<number, ProofLine[]>();
    for (const pl of lines) {
      for (let ln = pl.lean_span.start_line; ln <= pl.lean_span.end_line; ln++) {
        const list = map.get(ln) ?? [];
        list.push(pl);
        map.set(ln, list);
      }
    }
    return map;
  }, [lines]);

  const activeLineId = hoveredLineId ?? selectedLineId;
  const activeProofLine = useMemo(
    () => lines.find((l) => l.line_id === activeLineId) ?? null,
    [lines, activeLineId]
  );

  const handleRunRetranslate = async () => {
    setBusy(true);
    try {
      await onRetranslate(draftSource, fidelity);
      setEditMode(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="pane pane-lean">
      <div className="pane-header">
        <div className="pane-title-group">
          <Code2 size={15} />
          <span className="pane-title">Lean source code</span>
          <span className={`extractor-badge mode-${infotree.extractor_mode}`}>
            {infotree.extractor_mode === "lean4_infotree"
              ? "Live Lean 4 InfoTree"
              : infotree.extractor_mode === "precomputed_infotree"
              ? "Verified InfoTree"
              : "Heuristic Parser"}
          </span>
        </div>

        <div className="pane-actions">
          {!editMode ? (
            <button
              type="button"
              className="btn-xs btn-ghost"
              onClick={() => setEditMode(true)}
              title="Edit Lean 4 code and re-extract InfoTree"
            >
              Edit Lean
            </button>
          ) : (
            <>
              <select
                className="select-xs"
                value={fidelity}
                onChange={(e) => setFidelity(e.target.value as FidelityMode)}
              >
                <option value="literal">Literal</option>
                <option value="expanded">Expanded Automation</option>
                <option value="formal_prose">Formal Prose</option>
              </select>
              <button
                type="button"
                className="btn-xs btn-primary"
                disabled={busy}
                onClick={handleRunRetranslate}
              >
                <Play size={12} />
                {busy ? "Extracting…" : "Extract & Translate"}
              </button>
              <button
                type="button"
                className="btn-xs btn-ghost"
                onClick={() => {
                  setDraftSource(infotree.source_code);
                  setEditMode(false);
                }}
              >
                <RotateCcw size={12} />
                Cancel
              </button>
            </>
          )}
        </div>
      </div>

      {editMode ? (
        <div className="lean-editor-wrap">
          <div className="lean-editor-hint">
            <Sparkles size={13} />
            Modify Lean 4 tactics (or insert a <code>sorry</code> to test adversarial faithfulness detection), then click <strong>Extract &amp; Translate</strong>.
          </div>
          <textarea
            className="lean-textarea"
            value={draftSource}
            onChange={(e) => setDraftSource(e.target.value)}
            spellCheck={false}
          />
        </div>
      ) : (
        <div
          className="lean-code-scroll"
          ref={scrollContainerRef}
          onScroll={onScrollSync}
        >
          <div className="lean-code-list">
            {sourceLines.map((text, idx) => {
              const lineNum = idx + 1;
              const mapped = lineToProofLines.get(lineNum) ?? [];
              const primary = mapped[0] ?? null;
              const isInActiveSpan =
                activeProofLine !== null &&
                lineNum >= activeProofLine.lean_span.start_line &&
                lineNum <= activeProofLine.lean_span.end_line;
              const isSpanStart =
                primary !== null && primary.lean_span.start_line === lineNum;

              return (
                <div
                  key={lineNum}
                  ref={(el) => registerLeanLineRef(lineNum, el)}
                  className={[
                    "lean-line",
                    primary ? `mapped status-${primary.status}` : "unmapped",
                    isInActiveSpan ? "is-highlighted" : "",
                    primary?.derivation.opaque_automation ? "has-opaque" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onMouseEnter={() => primary && onHoverLine(primary.line_id)}
                  onMouseLeave={() => onHoverLine(null)}
                  onClick={() => primary && onSelectLine(primary.line_id)}
                >
                  <span className="lean-gutter-bar" />
                  <span className="lean-ln">{lineNum}</span>
                  <span className="lean-text">{highlightLeanLine(text || " ")}</span>
                  {isSpanStart && primary && (
                    <span className={`lean-anchor-chip status-${primary.status}`}>
                      → Step {primary.line_number}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
