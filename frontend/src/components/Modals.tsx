import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  Copy,
  Cpu,
  Download,
  FileCode2,
  FileText,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";
import { api } from "../api";
import type { FidelityMode, ModelConfig, TranslationSession } from "../types";

/* --- 1. Local Small LM Configuration Modal --- */
interface ModelConfigModalProps {
  open: boolean;
  onClose: () => void;
  onSaved: (cfg: ModelConfig) => void;
}

export const ModelConfigModal: React.FC<ModelConfigModalProps> = ({
  open,
  onClose,
  onSaved,
}) => {
  const [cfg, setCfg] = useState<ModelConfig | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    detail: string;
    available_models?: string[];
  } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setTestResult(null);
      api.getModelConfig().then(setCfg).catch(console.error);
    }
  }, [open]);

  if (!open || !cfg) return null;

  const handleTest = async () => {
    setTesting(true);
    try {
      const res = await api.testModelConnection(cfg);
      setTestResult(res);
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await api.updateModelConfig(cfg);
      onSaved(updated);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <Cpu size={17} /> Specialized Small LM Backend Configuration
          </div>
          <button type="button" className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <p className="modal-lead">
            Connect any local OpenAI-compatible open-weights server (<strong>Ollama</strong>,{" "}
            <strong>vLLM</strong>, <strong>llama.cpp</strong>, or <strong>SGLang</strong>) running a
            7B–32B specialized model fine-tuned on literal Lean 4 InfoTree pairs, or run zero-setup
            with the built-in Symbolic-Literal Baseline.
          </p>

          <div className="form-group">
            <label>Inference Engine</label>
            <div className="radio-card-row">
              <button
                type="button"
                className={`radio-card ${cfg.backend_mode === "symbolic_baseline" ? "is-selected" : ""}`}
                onClick={() => setCfg({ ...cfg, backend_mode: "symbolic_baseline" })}
              >
                <strong>Symbolic-Literal Baseline</strong>
                <span>Zero GPU / instant deterministic InfoTree mapping &amp; opaque-tactic auditing.</span>
              </button>
              <button
                type="button"
                className={`radio-card ${cfg.backend_mode === "openai_compatible_lm" ? "is-selected" : ""}`}
                onClick={() => setCfg({ ...cfg, backend_mode: "openai_compatible_lm" })}
              >
                <strong>Local Specialized Small LM (7B–32B)</strong>
                <span>Queries Ollama / vLLM / llama.cpp with strict adversarial JSON schema.</span>
              </button>
            </div>
          </div>

          {cfg.backend_mode === "openai_compatible_lm" && (
            <>
              <div className="form-row-2">
                <div className="form-group">
                  <label>Endpoint Base URL</label>
                  <input
                    className="text-input"
                    value={cfg.base_url}
                    onChange={(e) => setCfg({ ...cfg, base_url: e.target.value })}
                    placeholder="http://localhost:11434/v1"
                  />
                </div>
                <div className="form-group">
                  <label>Model ID (7B–32B Checkpoint)</label>
                  <input
                    className="text-input"
                    value={cfg.model_name}
                    onChange={(e) => setCfg({ ...cfg, model_name: e.target.value })}
                    placeholder="qwen2.5-math:7b-instruct"
                  />
                </div>
              </div>

              <div className="form-row-2">
                <div className="form-group">
                  <label>Temperature ({cfg.temperature})</label>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={cfg.temperature}
                    onChange={(e) => setCfg({ ...cfg, temperature: Number(e.target.value) })}
                  />
                </div>
                <div className="form-group">
                  <label>API Key (optional for local servers)</label>
                  <input
                    type="password"
                    className="text-input"
                    value={cfg.api_key}
                    onChange={(e) => setCfg({ ...cfg, api_key: e.target.value })}
                    placeholder="Empty for Ollama / local vLLM"
                  />
                </div>
              </div>
            </>
          )}

          {testResult && (
            <div className={`test-banner ${testResult.ok ? "is-ok" : "is-err"}`}>
              {testResult.ok ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
              <div>
                <div>{testResult.detail}</div>
                {testResult.available_models && testResult.available_models.length > 0 && (
                  <div className="model-pill-list">
                    {testResult.available_models.slice(0, 6).map((m) => (
                      <button
                        key={m}
                        type="button"
                        className="chip-lemma"
                        onClick={() => setCfg({ ...cfg, model_name: m })}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-sm btn-ghost" onClick={handleTest} disabled={testing}>
            {testing ? "Testing…" : "Test Connection"}
          </button>
          <div className="modal-footer-right">
            <button type="button" className="btn-sm btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="button" className="btn-sm btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save Configuration"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/* --- 2. New Custom Lean 4 Proof Modal --- */
interface NewProofModalProps {
  open: boolean;
  onClose: () => void;
  onCreate: (title: string, leanSource: string, fidelity: FidelityMode) => Promise<void>;
}

const CUSTOM_STARTER = `import Mathlib.Tactic

theorem even_sq_of_even (n : ℕ) (h : 2 ∣ n) : 2 ∣ n ^ 2 := by
  obtain ⟨k, hk⟩ := h
  have hsq : n ^ 2 = 2 * (2 * k ^ 2) := by
    rw [hk]
    ring
  exact ⟨2 * k ^ 2, hsq⟩
`;

export const NewProofModal: React.FC<NewProofModalProps> = ({ open, onClose, onCreate }) => {
  const [title, setTitle] = useState("Even Square Lemma");
  const [source, setSource] = useState(CUSTOM_STARTER);
  const [fidelity, setFidelity] = useState<FidelityMode>("literal");
  const [busy, setBusy] = useState(false);

  if (!open) return null;

  const submit = async () => {
    if (!source.trim()) return;
    setBusy(true);
    try {
      await onCreate(title.trim() || "Custom Lean 4 Proof", source, fidelity);
      onClose();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <FileCode2 size={17} /> Translate Custom Lean 4 Proof
          </div>
          <button type="button" className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <div className="modal-body">
          <div className="form-row-2">
            <div className="form-group">
              <label>Proof Title</label>
              <input
                className="text-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Initial Fidelity Mode</label>
              <select
                className="text-input"
                value={fidelity}
                onChange={(e) => setFidelity(e.target.value as FidelityMode)}
              >
                <option value="literal">Literal (Formal Symbolic)</option>
                <option value="expanded">Expanded Automation</option>
                <option value="formal_prose">Structured Mathematical Prose</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label>Lean 4 Source Code</label>
            <textarea
              className="lean-textarea modal-textarea"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              spellCheck={false}
            />
          </div>
        </div>
        <div className="modal-footer">
          <span className="modal-hint">
            Uses live Lean 4 <code>infotree_dumper</code> when installed, otherwise deterministic parser.
          </span>
          <div className="modal-footer-right">
            <button type="button" className="btn-sm btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="button" className="btn-sm btn-primary" disabled={busy} onClick={submit}>
              <Sparkles size={13} /> {busy ? "Translating…" : "Extract InfoTree & Translate"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/* --- 3. Export LaTeX & HITL Training Dataset Modal --- */
interface ExportModalProps {
  open: boolean;
  session: TranslationSession | null;
  onClose: () => void;
}

export const ExportModal: React.FC<ExportModalProps> = ({ open, session, onClose }) => {
  const [tab, setTab] = useState<"latex" | "dataset">("latex");
  const [includeProv, setIncludeProv] = useState(true);
  const [content, setContent] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open || !session) return;
    setCopied(false);
    if (tab === "latex") {
      api.exportLatexText(session.session_id, includeProv).then(setContent).catch(console.error);
    } else {
      api.exportDatasetText(session.session_id).then(setContent).catch(console.error);
    }
  }, [open, session, tab, includeProv]);

  if (!open || !session) return null;

  const recordCount =
    tab === "dataset"
      ? content
          .split("\n")
          .filter((l) => l.trim().length > 0).length
      : 0;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const handleDownload = () => {
    const ext = tab === "latex" ? "tex" : "hitl.jsonl";
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${session.infotree.theorem_name}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <FileText size={17} /> Export Proof &amp; HITL Fine-Tuning Dataset
          </div>
          <button type="button" className="icon-btn" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          <div className="export-tabs">
            <button
              type="button"
              className={`export-tab ${tab === "latex" ? "is-active" : ""}`}
              onClick={() => setTab("latex")}
            >
              LaTeX Document (.tex)
            </button>
            <button
              type="button"
              className={`export-tab ${tab === "dataset" ? "is-active" : ""}`}
              onClick={() => setTab("dataset")}
            >
              HITL Fine-Tuning Dataset (SFT + DPO .jsonl)
            </button>
          </div>

          {tab === "latex" ? (
            <label className="checkbox-field export-opt">
              <input
                type="checkbox"
                checked={includeProv}
                onChange={(e) => setIncludeProv(e.target.checked)}
              />
              <span>Include Lean line-range &amp; justification provenance comments (<code>% [LIT ...]</code>)</span>
            </label>
          ) : (
            <div className="dataset-banner">
              <strong>{recordCount} training record{recordCount === 1 ? "" : "s"} harvested</strong> from
              your Verified, Edited, and Flagged lines in this session. Feed directly into{" "}
              <code>python training/generate_adversarial_pairs.py --hitl-jsonl ...</code>
              {recordCount === 0 && (
                <div className="dataset-empty-tip">
                  Tip: Verify, edit, or flag at least one proof line to generate SFT &amp; DPO preference pairs!
                </div>
              )}
            </div>
          )}

          <pre className="export-preview">{content || "(No records yet)"}</pre>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-sm btn-ghost" onClick={handleCopy} disabled={!content}>
            <Copy size={13} /> {copied ? "Copied!" : "Copy to Clipboard"}
          </button>
          <div className="modal-footer-right">
            <button type="button" className="btn-sm btn-ghost" onClick={onClose}>
              Close
            </button>
            <button type="button" className="btn-sm btn-primary" onClick={handleDownload} disabled={!content}>
              <Download size={13} /> Download {tab === "latex" ? ".tex" : ".jsonl"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
