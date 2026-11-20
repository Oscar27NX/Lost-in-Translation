import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Cpu,
  Download,
  PanelRightClose,
  PanelRightOpen,
  Plus,
  Sparkles,
} from "lucide-react";
import { api } from "./api";
import { InspectorPanel } from "./components/InspectorPanel";
import { LatexProofPane } from "./components/LatexProofPane";
import { LeanSourcePane } from "./components/LeanSourcePane";
import { ExportModal, ModelConfigModal, NewProofModal } from "./components/Modals";
import { ProofOverviewBar, type FilterMode } from "./components/ProofOverviewBar";
import { ProvenanceRibbon, type RibbonEdge } from "./components/ProvenanceRibbon";
import type {
  ExampleSummary,
  FidelityMode,
  FlagCategory,
  HealthStatus,
  ModelConfig,
  ProofLine,
  TranslationSession,
} from "./types";

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [examples, setExamples] = useState<ExampleSummary[]>([]);
  const [session, setSession] = useState<TranslationSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  // Interactive visual coordination state
  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);
  const [hoveredLineId, setHoveredLineId] = useState<string | null>(null);
  const [filterMode, setFilterMode] = useState<FilterMode>("all");
  const [inspectorOpen, setInspectorOpen] = useState(false);

  // Inline HITL states
  const [editingLineId, setEditingLineId] = useState<string | null>(null);
  const [flaggingLineId, setFlaggingLineId] = useState<string | null>(null);
  const [regenLineId, setRegenLineId] = useState<string | null>(null);
  const [busyLineId, setBusyLineId] = useState<string | null>(null);

  // Modals
  const [modelModalOpen, setModelModalOpen] = useState(false);
  const [newProofModalOpen, setNewProofModalOpen] = useState(false);
  const [exportModalOpen, setExportModalOpen] = useState(false);

  // DOM refs for live SVG bipartite ribbon calculation
  const stageRef = useRef<HTMLDivElement>(null);
  const leanScrollRef = useRef<HTMLDivElement>(null);
  const latexScrollRef = useRef<HTMLDivElement>(null);
  const leanLineRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const latexCardRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const [ribbonEdges, setRibbonEdges] = useState<RibbonEdge[]>([]);
  const [ribbonHeight, setRibbonHeight] = useState(500);

  const showToast = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => {
      setToast((curr) => (curr === msg ? null : curr));
    }, 2800);
  }, []);

  // Boot: load health, curated examples, and default Irrationality of √2 session
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [h, exList] = await Promise.all([api.health(), api.listExamples()]);
        if (!active) return;
        setHealth(h);
        setExamples(exList);

        const initial = await api.createSession({
          example_key: "irrational_sqrt_two",
          fidelity_mode: "literal",
        });
        if (!active) return;
        setSession(initial);
        setSelectedLineId(null);
        setInspectorOpen(false);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filteredLines = useMemo(() => {
    if (!session) return [];
    switch (filterMode) {
      case "flagged":
        return session.lines.filter((l) => l.status === "flagged");
      case "opaque":
        return session.lines.filter((l) => l.derivation.opaque_automation);
      case "unreviewed":
        return session.lines.filter((l) => l.status === "unreviewed");
      case "edited":
        return session.lines.filter((l) => l.status === "edited");
      case "verified":
        return session.lines.filter((l) => l.status === "verified");
      default:
        return session.lines;
    }
  }, [session, filterMode]);

  const selectedLine = useMemo(
    () => session?.lines.find((l) => l.line_id === selectedLineId) ?? null,
    [session, selectedLineId]
  );

  // Measure live Lean span coordinates and LaTeX card coordinates for the center SVG ribbon
  const computeRibbons = useCallback(() => {
    const stageEl = stageRef.current;
    if (!stageEl || !session) return;
    const stageRect = stageEl.getBoundingClientRect();
    setRibbonHeight(stageRect.height);

    const edges: RibbonEdge[] = [];
    for (const line of filteredLines) {
      const cardEl = latexCardRefs.current.get(line.line_id);
      const startEl = leanLineRefs.current.get(line.lean_span.start_line);
      const endEl = leanLineRefs.current.get(line.lean_span.end_line) ?? startEl;
      if (!cardEl || !startEl || !endEl) continue;

      const cardRect = cardEl.getBoundingClientRect();
      const startRect = startEl.getBoundingClientRect();
      const endRect = endEl.getBoundingClientRect();

      // Skip edges completely clipped far outside viewport
      if (cardRect.bottom < stageRect.top - 120 || cardRect.top > stageRect.bottom + 120) {
        continue;
      }

      const clampY = (y: number) => Math.max(4, Math.min(stageRect.height - 4, y));
      const yLeftTop = clampY(startRect.top - stageRect.top + 3);
      const yLeftBottom = clampY(endRect.bottom - stageRect.top - 3);
      const yLeftMid = (yLeftTop + yLeftBottom) / 2;
      const yRightMid = clampY(cardRect.top + cardRect.height / 2 - stageRect.top);

      edges.push({
        line,
        yLeftTop: Math.min(yLeftTop, yLeftBottom),
        yLeftBottom: Math.max(yLeftTop, yLeftBottom),
        yLeftMid,
        yRightMid,
      });
    }
    setRibbonEdges(edges);
  }, [session, filteredLines]);

  const scheduleRibbonUpdate = useCallback(() => {
    window.requestAnimationFrame(computeRibbons);
  }, [computeRibbons]);

  useEffect(() => {
    scheduleRibbonUpdate();
    const timer = window.setTimeout(computeRibbons, 120);
    const ro = new ResizeObserver(scheduleRibbonUpdate);
    if (stageRef.current) ro.observe(stageRef.current);
    window.addEventListener("resize", scheduleRibbonUpdate);
    return () => {
      window.clearTimeout(timer);
      ro.disconnect();
      window.removeEventListener("resize", scheduleRibbonUpdate);
    };
  }, [
    computeRibbons,
    scheduleRibbonUpdate,
    session,
    filteredLines,
    inspectorOpen,
    editingLineId,
    flaggingLineId,
    regenLineId,
  ]);

  const registerLeanLineRef = useCallback((lineNum: number, el: HTMLDivElement | null) => {
    if (el) leanLineRefs.current.set(lineNum, el);
    else leanLineRefs.current.delete(lineNum);
  }, []);

  const registerLatexCardRef = useCallback((lineId: string, el: HTMLDivElement | null) => {
    if (el) latexCardRefs.current.set(lineId, el);
    else latexCardRefs.current.delete(lineId);
  }, []);

  const handleSelectLine = useCallback(
    (lineId: string, scrollIntoView = false, openInspector = true) => {
      setSelectedLineId(lineId);
      if (openInspector) {
        setInspectorOpen(true);
      }
      if (!session) return;
      const target = session.lines.find((l) => l.line_id === lineId);
      if (!target) return;

      if (scrollIntoView) {
        const cardEl = latexCardRefs.current.get(lineId);
        cardEl?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
      const leanEl = leanLineRefs.current.get(target.lean_span.start_line);
      leanEl?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      window.setTimeout(computeRibbons, 240);
    },
    [session, computeRibbons]
  );

  const handleGoToStep = useCallback(
    (rawStep: number) => {
      if (!session || session.lines.length === 0) return;
      if (!Number.isInteger(rawStep) || rawStep < 1) return;
      const clampedIdx = Math.min(rawStep, session.lines.length) - 1;
      const target = session.lines[clampedIdx];
      if (!target) return;

      const isVisible = filteredLines.some((l) => l.line_id === target.line_id);
      if (!isVisible) {
        setFilterMode("all");
        setSelectedLineId(target.line_id);
        window.setTimeout(() => {
          latexCardRefs.current
            .get(target.line_id)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
          leanLineRefs.current
            .get(target.lean_span.start_line)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
          window.setTimeout(computeRibbons, 220);
        }, 40);
      } else {
        handleSelectLine(target.line_id, true, false);
      }
    },
    [session, filteredLines, handleSelectLine, computeRibbons]
  );

  // Switch between curated examples
  const handleSelectExample = async (exampleKey: string) => {
    setLoading(true);
    setError(null);
    setFilterMode("all");
    setEditingLineId(null);
    setFlaggingLineId(null);
    setRegenLineId(null);
    try {
      const next = await api.createSession({ example_key: exampleKey, fidelity_mode: "literal" });
      setSession(next);
      setSelectedLineId(null);
      setInspectorOpen(false);
      showToast(`Loaded "${next.title}" (${next.lines.length} InfoTree steps)`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCustomProof = async (
    title: string,
    leanSource: string,
    fidelity: FidelityMode
  ) => {
    const next = await api.createSession({
      title,
      lean_source: leanSource,
      fidelity_mode: fidelity,
    });
    setSession(next);
    setFilterMode("all");
    setSelectedLineId(null);
    setInspectorOpen(false);
    showToast(`Extracted ${next.lines.length} proof steps from custom Lean 4 code`);
  };

  const handleRetranslate = async (leanSource: string, fidelity: FidelityMode) => {
    if (!session) return;
    const updated = await api.retranslate(session.session_id, leanSource, fidelity);
    setSession(updated);
    setSelectedLineId(null);
    setInspectorOpen(false);
    showToast(`Re-extracted & translated ${updated.lines.length} steps (${fidelity})`);
  };

  const handleVerifyLine = useCallback(
    async (line: ProofLine) => {
      if (!session) return;
      setBusyLineId(line.line_id);
      try {
        const nextStatus = line.status === "verified" ? "unreviewed" : "verified";
        const updated = await api.updateLine(session.session_id, line.line_id, {
          status: nextStatus,
        });
        setSession(updated);
        showToast(
          nextStatus === "verified"
            ? `Verified Step ${line.line_number} (added to SFT export pool)`
            : `Marked Step ${line.line_number} as unreviewed`
        );
      } finally {
        setBusyLineId(null);
      }
    },
    [session, showToast]
  );

  const handleSaveEdit = async (lineId: string, newLatex: string) => {
    if (!session) return;
    setBusyLineId(lineId);
    try {
      const updated = await api.updateLine(session.session_id, lineId, {
        latex: newLatex,
        status: "edited",
      });
      setSession(updated);
      setEditingLineId(null);
      showToast("Saved human LaTeX edit (DPO preference pair recorded)");
    } finally {
      setBusyLineId(null);
    }
  };

  const handleSubmitFlag = async (
    lineId: string,
    cats: FlagCategory[],
    comment: string
  ) => {
    if (!session) return;
    setBusyLineId(lineId);
    try {
      const updated = await api.updateLine(session.session_id, lineId, {
        flag_categories: cats,
        flag_comment: comment,
      });
      setSession(updated);
      setFlaggingLineId(null);
      showToast("Flagged step — critique ready for targeted regeneration & DPO export");
    } finally {
      setBusyLineId(null);
    }
  };

  const handleResolveFlags = async (lineId: string) => {
    if (!session) return;
    setBusyLineId(lineId);
    try {
      const updated = await api.updateLine(session.session_id, lineId, {
        resolve_flags: true,
        status: "verified",
      });
      setSession(updated);
      showToast("Resolved flags and marked line verified");
    } finally {
      setBusyLineId(null);
    }
  };

  const handleRegenerateLine = async (
    lineId: string,
    fidelity: FidelityMode,
    instruction: string,
    useActiveFlags: boolean
  ) => {
    if (!session) return;
    setBusyLineId(lineId);
    try {
      const updated = await api.regenerateLine(session.session_id, lineId, {
        fidelity_mode: fidelity,
        instruction: instruction.trim() || undefined,
        use_active_flags: useActiveFlags,
      });
      setSession(updated);
      setRegenLineId(null);
      showToast(`Regenerated single step (${fidelity}) — review new revision`);
    } catch (err) {
      showToast(`Regeneration failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBusyLineId(null);
    }
  };

  const handleRevertRevision = async (lineId: string, revIdx: number) => {
    if (!session) return;
    setBusyLineId(lineId);
    try {
      const updated = await api.revertRevision(session.session_id, lineId, revIdx);
      setSession(updated);
      showToast(`Restored revision v${revIdx + 1}`);
    } finally {
      setBusyLineId(null);
    }
  };

  const handleModelSaved = async (cfg: ModelConfig) => {
    const h = await api.health();
    setHealth(h);
    showToast(
      cfg.backend_mode === "openai_compatible_lm"
        ? `Switched backend to ${cfg.model_name}`
        : "Switched backend to Symbolic-Literal Baseline"
    );
  };

  // Keyboard-first audit workflow (j/k, v, f, e, r, Esc)
  useEffect(() => {
    const onKeyDown = (ev: KeyboardEvent) => {
      const target = ev.target as HTMLElement | null;
      if (
        target &&
        (target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.tagName === "SELECT" ||
          target.isContentEditable)
      ) {
        if (ev.key === "Escape") {
          setEditingLineId(null);
          setFlaggingLineId(null);
          setRegenLineId(null);
        }
        return;
      }
      if (modelModalOpen || newProofModalOpen || exportModalOpen) {
        if (ev.key === "Escape") {
          setModelModalOpen(false);
          setNewProofModalOpen(false);
          setExportModalOpen(false);
        }
        return;
      }
      if (!filteredLines.length) return;

      const idx = filteredLines.findIndex((l) => l.line_id === selectedLineId);
      if (ev.key === "j" || ev.key === "ArrowDown") {
        ev.preventDefault();
        const next = filteredLines[Math.min(filteredLines.length - 1, Math.max(0, idx + 1))];
        if (next) handleSelectLine(next.line_id, true, false);
      } else if (ev.key === "k" || ev.key === "ArrowUp") {
        ev.preventDefault();
        const prev = filteredLines[Math.max(0, idx - 1)];
        if (prev) handleSelectLine(prev.line_id, true, false);
      } else if (ev.key === "v" && selectedLine) {
        ev.preventDefault();
        handleVerifyLine(selectedLine);
      } else if (ev.key === "f" && selectedLine) {
        ev.preventDefault();
        setEditingLineId(null);
        setRegenLineId(null);
        setFlaggingLineId(selectedLine.line_id);
      } else if (ev.key === "e" && selectedLine) {
        ev.preventDefault();
        setFlaggingLineId(null);
        setRegenLineId(null);
        setEditingLineId(selectedLine.line_id);
      } else if (ev.key === "r" && selectedLine) {
        ev.preventDefault();
        setEditingLineId(null);
        setFlaggingLineId(null);
        setRegenLineId(selectedLine.line_id);
      } else if (ev.key === "Escape") {
        if (editingLineId || flaggingLineId || regenLineId) {
          setEditingLineId(null);
          setFlaggingLineId(null);
          setRegenLineId(null);
        } else if (inspectorOpen) {
          setInspectorOpen(false);
        }
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    filteredLines,
    selectedLineId,
    selectedLine,
    handleSelectLine,
    handleVerifyLine,
    editingLineId,
    flaggingLineId,
    regenLineId,
    inspectorOpen,
    modelModalOpen,
    newProofModalOpen,
    exportModalOpen,
  ]);

  return (
    <div className="app-shell">
      {/* Top Application Header */}
      <header className="top-header">
        <div className="brand-group">
          <h1 className="brand-name">Lost In Translation</h1>
        </div>

        <div className="header-controls">
          <div className="proof-switcher">
            <BookOpen size={14} className="switcher-icon" />
            <select
              aria-label="Select Proof Example"
              className="proof-select"
              value={session?.example_key ?? "__custom__"}
              onChange={(e) => {
                if (e.target.value !== "__custom__") {
                  handleSelectExample(e.target.value);
                }
              }}
            >
              {examples.map((ex) => (
                <option key={ex.key} value={ex.key}>
                  {ex.title} ({ex.line_count} steps)
                </option>
              ))}
              {session && !session.example_key && (
                <option value="__custom__">{session.title} (Custom)</option>
              )}
            </select>
          </div>

          <button
            type="button"
            className="btn-sm btn-ghost"
            onClick={() => setNewProofModalOpen(true)}
          >
            <Plus size={14} /> Custom Lean 4
          </button>

          <button
            type="button"
            className={`backend-pill ${health?.backend_mode === "openai_compatible_lm" ? "is-lm" : ""}`}
            onClick={() => setModelModalOpen(true)}
            title="Configure local 7B–32B specialized LM (Ollama / vLLM) or Symbolic Baseline"
          >
            <Cpu size={13} />
            <span>
              {health?.backend_mode === "openai_compatible_lm"
                ? `LM: ${health.model_name}`
                : "Symbolic-Literal Baseline"}
            </span>
          </button>

          <button
            type="button"
            className="btn-sm btn-primary"
            disabled={!session}
            onClick={() => setExportModalOpen(true)}
          >
            <Download size={14} /> Export .tex / DPO
          </button>

          <button
            type="button"
            className="icon-btn"
            onClick={() => setInspectorOpen((v) => !v)}
            title={inspectorOpen ? "Collapse Provenance Inspector" : "Expand Provenance Inspector"}
          >
            {inspectorOpen ? <PanelRightClose size={17} /> : <PanelRightOpen size={17} />}
          </button>
        </div>
      </header>

      {/* Main Content */}
      {loading && !session ? (
        <div className="center-state">
          <Sparkles size={22} className="spin" />
          <p>Loading Lean 4 InfoTree &amp; faithful translation workspace…</p>
        </div>
      ) : error ? (
        <div className="center-state is-error">
          <p>Could not connect to Lost In Translation backend: {error}</p>
          <p className="error-hint">
            Ensure the FastAPI server is running on <code>http://127.0.0.1:8000</code>.
          </p>
        </div>
      ) : session ? (
        <>
          <ProofOverviewBar
            lines={session.lines}
            metrics={session.metrics}
            filterMode={filterMode}
            onFilterChange={setFilterMode}
            onGoToStep={handleGoToStep}
          />

          <main
            className={`workbench-grid ${inspectorOpen ? "with-inspector" : "no-inspector"}`}
          >
            <div className="workbench-stage" ref={stageRef}>
              <LeanSourcePane
                infotree={session.infotree}
                lines={session.lines}
                selectedLineId={selectedLineId}
                hoveredLineId={hoveredLineId}
                onSelectLine={(id) => handleSelectLine(id, true)}
                onHoverLine={setHoveredLineId}
                onRetranslate={handleRetranslate}
                scrollContainerRef={leanScrollRef}
                registerLeanLineRef={registerLeanLineRef}
                onScrollSync={scheduleRibbonUpdate}
              />

              <ProvenanceRibbon
                edges={ribbonEdges}
                height={ribbonHeight}
                selectedLineId={selectedLineId}
                hoveredLineId={hoveredLineId}
                onSelectLine={(id) => handleSelectLine(id, true)}
                onHoverLine={setHoveredLineId}
              />

              <LatexProofPane
                infotree={session.infotree}
                lines={filteredLines}
                selectedLineId={selectedLineId}
                hoveredLineId={hoveredLineId}
                editingLineId={editingLineId}
                flaggingLineId={flaggingLineId}
                regenLineId={regenLineId}
                busyLineId={busyLineId}
                onSelectLine={(id) => handleSelectLine(id, false)}
                onHoverLine={setHoveredLineId}
                onStartEdit={setEditingLineId}
                onStartFlag={setFlaggingLineId}
                onStartRegen={setRegenLineId}
                onVerifyLine={handleVerifyLine}
                onSaveEdit={handleSaveEdit}
                onSubmitFlag={handleSubmitFlag}
                onRegenerateLine={handleRegenerateLine}
                scrollContainerRef={latexScrollRef}
                registerLatexCardRef={registerLatexCardRef}
                onScrollSync={scheduleRibbonUpdate}
              />
            </div>

            {inspectorOpen && (
              <InspectorPanel
                infotree={session.infotree}
                line={selectedLine}
                busy={busyLineId !== null}
                onClose={() => setInspectorOpen(false)}
                onRevertRevision={handleRevertRevision}
                onResolveFlags={handleResolveFlags}
              />
            )}
          </main>
        </>
      ) : null}

      {/* Modals */}
      <ModelConfigModal
        open={modelModalOpen}
        onClose={() => setModelModalOpen(false)}
        onSaved={handleModelSaved}
      />
      <NewProofModal
        open={newProofModalOpen}
        onClose={() => setNewProofModalOpen(false)}
        onCreate={handleCreateCustomProof}
      />
      <ExportModal
        open={exportModalOpen}
        session={session}
        onClose={() => setExportModalOpen(false)}
      />

      {toast && (
        <div className="toast-banner" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}
