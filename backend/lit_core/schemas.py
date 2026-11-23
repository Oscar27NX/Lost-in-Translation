from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from .latex_fmt import strip_lean_comments_preserving_lines


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class LineStatus(StrEnum):
    UNREVIEWED = "unreviewed"
    VERIFIED = "verified"
    FLAGGED = "flagged"
    EDITED = "edited"


class FlagCategory(StrEnum):
    SEMANTIC_DRIFT = "semantic_drift"
    MISSING_HYPOTHESIS = "missing_hypothesis"
    QUANTIFIER_TYPE_ERROR = "quantifier_type_error"
    OPAQUE_TACTIC_ELISION = "opaque_tactic_elision"
    NOTATION_MISMATCH = "notation_mismatch"
    HALLUCINATED_STEP = "hallucinated_step"


class FidelityMode(StrEnum):
    LITERAL = "literal"
    EXPANDED = "expanded"
    FORMAL_PROSE = "formal_prose"


class Span(BaseModel):
    start_line: int = Field(..., ge=1, description="1-based inclusive start line in Lean source")
    end_line: int = Field(..., ge=1, description="1-based inclusive end line in Lean source")
    start_col: int = Field(default=1, ge=1)
    end_col: int = Field(default=1, ge=1)


class Hypothesis(BaseModel):
    name: str
    type: str
    change: Literal["unchanged", "added", "modified", "consumed"] = "unchanged"


class GoalState(BaseModel):
    tag: str = ""
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    target: str = ""
    pretty: str = ""


class InfoTreeNode(BaseModel):
    node_id: str
    parent_id: str | None = None
    depth: int = 0
    kind: str = "tactic"
    tactic_kind: str = ""
    span: Span
    source_slice: str = ""
    goals_before: list[GoalState] = Field(default_factory=list)
    goals_after: list[GoalState] = Field(default_factory=list)
    referenced_constants: list[str] = Field(default_factory=list)
    is_opaque_automation: bool = False


class InfoTreeDocument(BaseModel):
    theorem_name: str
    statement_lean: str
    statement_latex: str
    source_code: str
    lean_version: str = "4.12.0"
    extractor_mode: Literal["lean4_infotree", "precomputed_infotree", "heuristic_parser"] = "precomputed_infotree"
    nodes: list[InfoTreeNode] = Field(default_factory=list)


class FaithfulnessCheck(BaseModel):
    name: str
    status: Literal["pass", "warn", "fail"]
    detail: str


class DerivationMeta(BaseModel):
    procedure: list[str] = Field(
        default_factory=list,
        description="Ordered step-by-step account of how the LaTeX output was derived from the InfoTree span.",
    )
    justification: str = Field(
        ...,
        description="Concise mathematical and syntactic rationale linking Lean tactics to LaTeX symbols.",
    )
    tactics_used: list[str] = Field(default_factory=list)
    referenced_lemmas: list[str] = Field(default_factory=list)
    model_id: str = "lit-symbolic-literal-v0.1"
    fidelity_mode: FidelityMode = FidelityMode.LITERAL
    confidence: float = Field(default=0.88, ge=0.0, le=1.0)
    opaque_automation: bool = False
    checks: list[FaithfulnessCheck] = Field(default_factory=list)


class FlagRecord(BaseModel):
    id: str
    categories: list[FlagCategory]
    comment: str = ""
    created_at: str = Field(default_factory=utc_now_iso)
    resolved: bool = False


class LineRevision(BaseModel):
    revision_index: int
    latex: str
    source: Literal["initial_inference", "human_edit", "regeneration"]
    model_id: str
    fidelity_mode: FidelityMode = FidelityMode.LITERAL
    instruction: str | None = None
    justification: str = ""
    created_at: str = Field(default_factory=utc_now_iso)


class ProofLine(BaseModel):
    line_id: str
    line_number: int = Field(..., ge=1, description="1-based index z in the rendered LaTeX proof")
    section_label: str = ""
    indent_level: int = Field(default=0, ge=0, le=4)
    latex: str
    original_latex: str
    lean_span: Span
    infotree_node_ids: list[str] = Field(default_factory=list)
    status: LineStatus = LineStatus.UNREVIEWED
    derivation: DerivationMeta
    flags: list[FlagRecord] = Field(default_factory=list)
    revisions: list[LineRevision] = Field(default_factory=list)


class SessionMetrics(BaseModel):
    total_lines: int
    verified_count: int
    flagged_count: int
    edited_count: int
    unreviewed_count: int
    opaque_tactic_count: int
    mean_confidence: float
    lean_line_coverage: float


class TranslationSession(BaseModel):
    session_id: str
    title: str
    subtitle: str = ""
    example_key: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    infotree: InfoTreeDocument
    lines: list[ProofLine] = Field(default_factory=list)
    model_id: str = "lit-symbolic-literal-v0.1"
    backend_mode: Literal["symbolic_baseline", "openai_compatible_lm"] = "symbolic_baseline"

    def compute_metrics(self) -> SessionMetrics:
        total = len(self.lines)
        if total == 0:
            return SessionMetrics(
                total_lines=0,
                verified_count=0,
                flagged_count=0,
                edited_count=0,
                unreviewed_count=0,
                opaque_tactic_count=0,
                mean_confidence=0.0,
                lean_line_coverage=0.0,
            )
        verified = sum(1 for pl in self.lines if pl.status == LineStatus.VERIFIED)
        flagged = sum(1 for pl in self.lines if pl.status == LineStatus.FLAGGED)
        edited = sum(1 for pl in self.lines if pl.status == LineStatus.EDITED)
        unreviewed = sum(1 for pl in self.lines if pl.status == LineStatus.UNREVIEWED)
        opaque = sum(1 for pl in self.lines if pl.derivation.opaque_automation)
        mean_conf = round(sum(pl.derivation.confidence for pl in self.lines) / total, 3)

        clean_lines = strip_lean_comments_preserving_lines(self.infotree.source_code).splitlines()
        non_proof_prefixes = (
            "import ",
            "open ",
            "namespace ",
            "end ",
            "section ",
            "set_option ",
            "variable ",
            "universe ",
            "attribute ",
            "termination_by ",
            "decreasing_by ",
        )
        proof_lines = {
            idx + 1
            for idx, txt in enumerate(clean_lines)
            if txt.strip()
            and not txt.strip().startswith(non_proof_prefixes)
            and txt.strip() not in ("end", "section")
        }
        covered: set[int] = set()
        for line in self.lines:
            for ln in range(line.lean_span.start_line, line.lean_span.end_line + 1):
                if ln in proof_lines:
                    covered.add(ln)
        coverage = round(len(covered) / max(len(proof_lines), 1), 3)
        return SessionMetrics(
            total_lines=total,
            verified_count=verified,
            flagged_count=flagged,
            edited_count=edited,
            unreviewed_count=unreviewed,
            opaque_tactic_count=opaque,
            mean_confidence=mean_conf,
            lean_line_coverage=coverage,
        )


class ModelConfig(BaseModel):
    backend_mode: Literal["symbolic_baseline", "openai_compatible_lm"] = "symbolic_baseline"
    symbolic_variant: Literal["symbolic_literal_v0_1", "symbolic_literal_v0_2"] = "symbolic_literal_v0_2"
    base_url: str = "http://localhost:11434/v1"
    model_name: str = "qwen2.5-math:7b-instruct"
    api_key: str = ""
    temperature: float = Field(default=0.15, ge=0.0, le=1.5)
    default_fidelity: FidelityMode = FidelityMode.LITERAL


# --- API Request / Response Payloads ---

class CreateSessionRequest(BaseModel):
    example_key: str | None = None
    title: str | None = None
    lean_source: str | None = None
    fidelity_mode: FidelityMode = FidelityMode.LITERAL


class UpdateLineRequest(BaseModel):
    latex: str | None = None
    status: LineStatus | None = None
    flag_categories: list[FlagCategory] | None = None
    flag_comment: str | None = None
    resolve_flags: bool | None = None


class RegenerateLineRequest(BaseModel):
    fidelity_mode: FidelityMode = FidelityMode.LITERAL
    instruction: str | None = None
    use_active_flags: bool = True
    temperature: float | None = Field(default=None, ge=0.0, le=1.5)


class RetranslateRequest(BaseModel):
    lean_source: str
    fidelity_mode: FidelityMode = FidelityMode.LITERAL


class ExampleSummary(BaseModel):
    key: str
    title: str
    subtitle: str
    theorem_name: str
    difficulty: str
    line_count: int
    statement_latex: str
