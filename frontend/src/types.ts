export type LineStatus = "unreviewed" | "verified" | "flagged" | "edited";

export type FlagCategory =
  | "semantic_drift"
  | "missing_hypothesis"
  | "quantifier_type_error"
  | "opaque_tactic_elision"
  | "notation_mismatch"
  | "hallucinated_step";

export type FidelityMode = "literal" | "expanded" | "formal_prose";

export interface Span {
  start_line: number;
  end_line: number;
  start_col: number;
  end_col: number;
}

export interface Hypothesis {
  name: string;
  type: string;
  change: "unchanged" | "added" | "modified" | "consumed";
}

export interface GoalState {
  tag: string;
  hypotheses: Hypothesis[];
  target: string;
  pretty: string;
}

export interface InfoTreeNode {
  node_id: string;
  parent_id: string | null;
  depth: number;
  kind: string;
  tactic_kind: string;
  span: Span;
  source_slice: string;
  goals_before: GoalState[];
  goals_after: GoalState[];
  referenced_constants: string[];
  is_opaque_automation: boolean;
}

export interface InfoTreeDocument {
  theorem_name: string;
  statement_lean: string;
  statement_latex: string;
  source_code: string;
  lean_version: string;
  extractor_mode: "lean4_infotree" | "precomputed_infotree" | "heuristic_parser";
  nodes: InfoTreeNode[];
}

export interface FaithfulnessCheck {
  name: string;
  status: "pass" | "warn" | "fail";
  detail: string;
}

export interface DerivationMeta {
  procedure: string[];
  justification: string;
  tactics_used: string[];
  referenced_lemmas: string[];
  model_id: string;
  fidelity_mode: FidelityMode;
  confidence: number;
  opaque_automation: boolean;
  checks: FaithfulnessCheck[];
}

export interface FlagRecord {
  id: string;
  categories: FlagCategory[];
  comment: string;
  created_at: string;
  resolved: boolean;
}

export interface LineRevision {
  revision_index: number;
  latex: string;
  source: "initial_inference" | "human_edit" | "regeneration";
  model_id: string;
  fidelity_mode: FidelityMode;
  instruction?: string | null;
  justification: string;
  created_at: string;
}

export interface ProofLine {
  line_id: string;
  line_number: number;
  section_label: string;
  indent_level: number;
  latex: string;
  original_latex: string;
  lean_span: Span;
  infotree_node_ids: string[];
  status: LineStatus;
  derivation: DerivationMeta;
  flags: FlagRecord[];
  revisions: LineRevision[];
}

export interface SessionMetrics {
  total_lines: number;
  verified_count: number;
  flagged_count: number;
  edited_count: number;
  unreviewed_count: number;
  opaque_tactic_count: number;
  mean_confidence: number;
  lean_line_coverage: number;
}

export interface TranslationSession {
  session_id: string;
  title: string;
  subtitle: string;
  example_key: string | null;
  created_at: string;
  updated_at: string;
  infotree: InfoTreeDocument;
  lines: ProofLine[];
  model_id: string;
  backend_mode: "symbolic_baseline" | "openai_compatible_lm";
  metrics: SessionMetrics;
}

export interface ExampleSummary {
  key: string;
  title: string;
  subtitle: string;
  theorem_name: string;
  difficulty: string;
  line_count: number;
  statement_latex: string;
}

export interface ModelConfig {
  backend_mode: "symbolic_baseline" | "openai_compatible_lm";
  base_url: string;
  model_name: string;
  api_key: string;
  temperature: number;
  default_fidelity: FidelityMode;
}

export interface HealthStatus {
  status: string;
  version: string;
  lean4_cli_available: boolean;
  backend_mode: "symbolic_baseline" | "openai_compatible_lm";
  model_name: string;
}

export const FLAG_CATEGORY_META: Record<
  FlagCategory,
  { label: string; short: string; description: string }
> = {
  semantic_drift: {
    label: "Semantic Drift",
    short: "Drift",
    description: "Mathematical meaning diverges from the elaborated Lean proof step.",
  },
  missing_hypothesis: {
    label: "Missing Hypothesis",
    short: "Missing Hyp",
    description: "Drops a required premise, side condition, or context variable.",
  },
  quantifier_type_error: {
    label: "Quantifier / Type Error",
    short: "Type/Quant",
    description: "Flips ∀/∃ scope or conflates domain coercions (e.g. ℕ vs ℤ vs ℝ).",
  },
  opaque_tactic_elision: {
    label: "Opaque Tactic Elision",
    short: "Opaque Tactic",
    description: "Hides nontrivial algebra inside linarith/omega/simp without unpacking.",
  },
  notation_mismatch: {
    label: "Notation Mismatch",
    short: "Notation",
    description: "Symbol choice conflicts with Lean definitions or surrounding steps.",
  },
  hallucinated_step: {
    label: "Hallucinated Step",
    short: "Hallucination",
    description: "Invents reasoning or masks a sorry not justified by the InfoTree.",
  },
};
