from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import (
    DerivationMeta,
    ExampleSummary,
    FaithfulnessCheck,
    FidelityMode,
    GoalState,
    Hypothesis,
    InfoTreeDocument,
    InfoTreeNode,
    LineRevision,
    LineStatus,
    ProofLine,
    Span,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "lean_extractor" / "examples"


def _read_example_source(filename: str) -> str:
    return (EXAMPLES_DIR / filename).read_text(encoding="utf-8")


def _slice_lines(source: str, start_line: int, end_line: int) -> str:
    lines = source.splitlines()
    return "\n".join(lines[start_line - 1 : end_line]).strip()


@dataclass
class CuratedExample:
    key: str
    title: str
    subtitle: str
    difficulty: str
    infotree: InfoTreeDocument
    literal_lines: list[dict[str, Any]]
    expanded_overrides: dict[str, tuple[str, list[str], str]]
    prose_overrides: dict[str, tuple[str, list[str], str]]


def _build_irrational_sqrt_two() -> CuratedExample:
    src = _read_example_source("IrrationalSqrt2.lean")

    def node(
        nid: str,
        start: int,
        end: int,
        tactic: str,
        before: GoalState,
        after: GoalState,
        refs: list[str],
        depth: int = 0,
        parent: str | None = None,
        opaque: bool = False,
    ) -> InfoTreeNode:
        return InfoTreeNode(
            node_id=nid,
            parent_id=parent,
            depth=depth,
            kind="tactic",
            tactic_kind=tactic,
            span=Span(start_line=start, end_line=end, start_col=1, end_col=80),
            source_slice=_slice_lines(src, start, end),
            goals_before=[before],
            goals_after=[after],
            referenced_constants=refs,
            is_opaque_automation=opaque,
        )

    h_q = Hypothesis(name="q", type="ℚ", change="added")
    h_hq = Hypothesis(name="hq", type="(q : ℝ) = Real.sqrt 2", change="added")
    h_q_u = Hypothesis(name="q", type="ℚ")
    h_hq_u = Hypothesis(name="hq", type="(q : ℝ) = Real.sqrt 2")
    h_cop = Hypothesis(name="hcop", type="Nat.Coprime q.num.natAbs q.den", change="added")
    h_cop_u = Hypothesis(name="hcop", type="Nat.Coprime q.num.natAbs q.den")
    h_bpos = Hypothesis(name="hb_pos", type="(0 : ℝ) < q.den", change="added")
    h_bpos_u = Hypothesis(name="hb_pos", type="(0 : ℝ) < q.den")
    h_sq_r = Hypothesis(name="hsq_real", type="((q.num : ℝ) / (q.den : ℝ)) ^ 2 = 2", change="added")
    h_sq_r_u = Hypothesis(name="hsq_real", type="((q.num : ℝ) / (q.den : ℝ)) ^ 2 = 2")
    h_sq_n = Hypothesis(name="hsq_nat", type="q.num.natAbs ^ 2 = 2 * q.den ^ 2", change="added")
    h_sq_n_u = Hypothesis(name="hsq_nat", type="q.num.natAbs ^ 2 = 2 * q.den ^ 2")
    h_2asq = Hypothesis(name="h2_dvd_a_sq", type="2 ∣ q.num.natAbs ^ 2", change="added")
    h_2a = Hypothesis(name="h2_dvd_a", type="2 ∣ q.num.natAbs", change="added")
    h_2a_u = Hypothesis(name="h2_dvd_a", type="2 ∣ q.num.natAbs")
    h_k = Hypothesis(name="k", type="ℕ", change="added")
    h_hk = Hypothesis(name="hk", type="q.num.natAbs = 2 * k", change="added")
    h_2bsq = Hypothesis(name="h2b_sq", type="q.den ^ 2 = 2 * k ^ 2", change="added")
    h_2bsq_u = Hypothesis(name="h2b_sq", type="q.den ^ 2 = 2 * k ^ 2")
    h_2b_dvd_sq = Hypothesis(name="h2_dvd_b_sq", type="2 ∣ q.den ^ 2", change="added")
    h_2b = Hypothesis(name="h2_dvd_b", type="2 ∣ q.den", change="added")
    h_2b_u = Hypothesis(name="h2_dvd_b", type="2 ∣ q.den")
    h_2gcd = Hypothesis(name="h2_dvd_gcd", type="2 ∣ Nat.gcd q.num.natAbs q.den", change="added")
    h_2gcd_one = Hypothesis(name="h2_dvd_gcd", type="2 ∣ 1", change="modified")

    nodes = [
        node(
            "n1",
            6,
            7,
            "Lean.Parser.Tactic.intro",
            GoalState(tag="main", hypotheses=[], target="Irrational (Real.sqrt 2)"),
            GoalState(tag="main", hypotheses=[h_q, h_hq], target="False"),
            ["Irrational", "Real.sqrt", "Rat.cast"],
        ),
        node(
            "n2",
            9,
            10,
            "Lean.Parser.Tactic.have",
            GoalState(tag="main", hypotheses=[h_q_u, h_hq_u], target="False"),
            GoalState(tag="main", hypotheses=[h_q_u, h_hq_u, h_cop, h_bpos], target="False"),
            ["Rat.reduced", "Rat.pos", "Nat.Coprime", "Nat.cast_pos"],
        ),
        node(
            "n3",
            12,
            13,
            "Lean.Parser.Tactic.rwSeq",
            GoalState(tag="main", hypotheses=[h_q_u, h_hq_u, h_cop_u, h_bpos_u], target="False"),
            GoalState(tag="main", hypotheses=[h_q_u, h_hq_u, h_cop_u, h_bpos_u, h_sq_r], target="False"),
            ["Rat.cast_def", "Real.sq_sqrt", "norm_num"],
        ),
        node(
            "n4",
            15,
            22,
            "Mathlib.Tactic.Linarith.linarith",
            GoalState(tag="main", hypotheses=[h_q_u, h_hq_u, h_cop_u, h_bpos_u, h_sq_r_u], target="False"),
            GoalState(tag="main", hypotheses=[h_q_u, h_hq_u, h_cop_u, h_bpos_u, h_sq_r_u, h_sq_n], target="False"),
            ["field_simp", "ne_of_gt", "linarith", "exact_mod_cast", "zify", "sq_abs"],
            depth=1,
            opaque=True,
        ),
        node(
            "n5",
            24,
            25,
            "Lean.Parser.Tactic.have",
            GoalState(tag="main", hypotheses=[h_q_u, h_cop_u, h_sq_n_u], target="False"),
            GoalState(tag="main", hypotheses=[h_q_u, h_cop_u, h_sq_n_u, h_2asq, h_2a], target="False"),
            ["Nat.Prime.dvd_of_dvd_pow", "Nat.prime_two"],
        ),
        node(
            "n6",
            27,
            30,
            "Mathlib.Tactic.Linarith.linarith",
            GoalState(tag="main", hypotheses=[h_q_u, h_cop_u, h_sq_n_u, h_2a_u], target="False"),
            GoalState(tag="main", hypotheses=[h_q_u, h_cop_u, h_sq_n_u, h_k, h_hk, h_2bsq], target="False"),
            ["obtain", "rw", "linarith"],
            depth=1,
            opaque=True,
        ),
        node(
            "n7",
            32,
            33,
            "Lean.Parser.Tactic.have",
            GoalState(tag="main", hypotheses=[h_cop_u, h_2a_u, h_2bsq_u], target="False"),
            GoalState(tag="main", hypotheses=[h_cop_u, h_2a_u, h_2bsq_u, h_2b_dvd_sq, h_2b], target="False"),
            ["Nat.Prime.dvd_of_dvd_pow", "Nat.prime_two"],
        ),
        node(
            "n8",
            35,
            37,
            "Mathlib.Meta.NormNum.normNum",
            GoalState(tag="main", hypotheses=[h_cop_u, h_2a_u, h_2b_u], target="False"),
            GoalState(tag="main", hypotheses=[h_cop_u, h_2gcd, h_2gcd_one], target="Goals accomplished ⊢ ⊥"),
            ["Nat.dvd_gcd", "Nat.Coprime.gcd_eq_one", "norm_num"],
            opaque=True,
        ),
    ]

    infotree = InfoTreeDocument(
        theorem_name="irrational_sqrt_two",
        statement_lean="theorem irrational_sqrt_two : Irrational (Real.sqrt 2)",
        statement_latex=r"\sqrt{2} \notin \mathbb{Q}",
        source_code=src,
        lean_version="4.12.0",
        extractor_mode="precomputed_infotree",
        nodes=nodes,
    )

    literal_lines = [
        {
            "line_id": "sqrt2-L1",
            "section_label": "Assumption for Contradiction",
            "indent_level": 0,
            "lean_span": Span(start_line=6, end_line=7),
            "infotree_node_ids": ["n1"],
            "latex": r"\text{Assume for contradiction that } \sqrt{2} \in \mathbb{Q}\text{, i.e., there exists } q \in \mathbb{Q} \text{ such that } (q : \mathbb{R}) = \sqrt{2}.",
            "derivation": DerivationMeta(
                procedure=[
                    "Unfold `Irrational (Real.sqrt 2)` := `Real.sqrt 2 ∉ Set.range (Rat.cast : ℚ → ℝ)` from InfoTree goalBefore.",
                    "Match `intro ⟨q, hq⟩` destructuring the existential witness `q : ℚ` and equality `hq : (q : ℝ) = Real.sqrt 2`.",
                    "Target transforms to `False`, establishing a proof by contradiction.",
                ],
                justification="Direct structural correspondence: `Irrational x` in Mathlib is defined as `x ∉ Set.range ((↑) : ℚ → ℝ)`, so `intro ⟨q, hq⟩` introduces a rational witness `q` whose real coercion equals √2.",
                tactics_used=["intro"],
                referenced_lemmas=["Irrational", "Real.sqrt"],
                confidence=0.97,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="quantifier_binding", status="pass", detail="Witness q : ℚ matches InfoTree binder exactly."),
                    FaithfulnessCheck(name="goal_polarity", status="pass", detail="Negation elimination to ⊢ False preserved."),
                ],
            ),
        },
        {
            "line_id": "sqrt2-L2",
            "section_label": "Canonical Reduced Fraction",
            "indent_level": 0,
            "lean_span": Span(start_line=9, end_line=10),
            "infotree_node_ids": ["n2"],
            "latex": r"\text{Write } q = \frac{a}{b} \text{ with } a = q.\mathrm{num} \in \mathbb{Z},\; b = q.\mathrm{den} \in \mathbb{N},\; b > 0,\text{ and } \gcd(|a|, b) = 1.",
            "derivation": DerivationMeta(
                procedure=[
                    "Read `hcop : Nat.Coprime q.num.natAbs q.den` justified by `q.reduced`.",
                    "Read `hb_pos : (0 : ℝ) < q.den` lifted from `q.pos : 0 < q.den` via `Nat.cast_pos.mpr`.",
                    "Introduce aliases a := q.num and b := q.den while preserving the signed-integer vs. natural-number distinction (|a| = q.num.natAbs).",
                ],
                justification="Preserves Lean's `Rat` structure fields (`num : ℤ`, `den : ℕ`, `pos`, `reduced`) explicitly; avoids falsely asserting a ∈ ℕ before taking |a|.",
                tactics_used=["have"],
                referenced_lemmas=["Rat.reduced", "Rat.pos", "Nat.Coprime", "Nat.cast_pos"],
                confidence=0.94,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="type_domain_fidelity", status="pass", detail="Retains a ∈ ℤ and |a| ∈ ℕ matching q.num.natAbs."),
                    FaithfulnessCheck(name="hypothesis_coverage", status="pass", detail="Both hcop and hb_pos represented."),
                ],
            ),
        },
        {
            "line_id": "sqrt2-L3",
            "section_label": "Squaring in ℝ",
            "indent_level": 0,
            "lean_span": Span(start_line=12, end_line=13),
            "infotree_node_ids": ["n3"],
            "latex": r"\text{Since } (q : \mathbb{R}) = \frac{a}{b} = \sqrt{2} \text{ and } 0 \le 2\text{, squaring gives } \left(\frac{a}{b}\right)^2 = (\sqrt{2})^2 = 2.",
            "derivation": DerivationMeta(
                procedure=[
                    "Trace `rw [← Rat.cast_def]` rewriting `(a : ℝ) / (b : ℝ)` to `(q : ℝ)`.",
                    "Rewrite using `hq : (q : ℝ) = Real.sqrt 2`.",
                    "Apply `Real.sq_sqrt` with nonnegativity side-condition `0 ≤ (2 : ℝ)` discharged by `norm_num`.",
                ],
                justification="Every rewrite in `rw [...]` maps 1-to-1 to the chain `(a/b)^2 = q^2 = (√2)^2 = 2`, explicitly citing `0 ≤ 2` required by `Real.sq_sqrt`.",
                tactics_used=["have", "rw", "norm_num"],
                referenced_lemmas=["Rat.cast_def", "Real.sq_sqrt"],
                confidence=0.95,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="side_condition_preserved", status="pass", detail="Nonnegativity premise 0 ≤ 2 explicitly retained."),
                    FaithfulnessCheck(name="rewrite_trace", status="pass", detail="All 3 rewrite lemmas accounted for."),
                ],
            ),
        },
        {
            "line_id": "sqrt2-L4",
            "section_label": "Clearing Denominators & Coercion to ℕ",
            "indent_level": 0,
            "lean_span": Span(start_line=15, end_line=22),
            "infotree_node_ids": ["n4"],
            "latex": r"\text{Multiplying by } b^2 > 0 \text{ yields } a^2 = 2b^2 \text{ in } \mathbb{R}\text{; by injectivity of } \mathbb{Z} \hookrightarrow \mathbb{R} \text{ and } |a|^2 = a^2,\; |a|^2 = 2b^2 \text{ in } \mathbb{N}.",
            "derivation": DerivationMeta(
                procedure=[
                    "`field_simp [ne_of_gt hb_pos]` clears denominator `b ≠ 0` from `hsq_real`.",
                    "`linarith` closes `(a : ℝ)^2 = 2 * (b : ℝ)^2` (opaque linear arithmetic decision procedure).",
                    "`exact_mod_cast` descends from ℝ to ℤ (`hint : a^2 = 2 * b^2`).",
                    "`zify; rw [sq_abs]; exact hint` lifts the ℕ goal `|a|^2 = 2 * b^2` to ℤ and identifies `|a|^2 = a^2`.",
                ],
                justification="Combines four coercion/algebra substeps into one equation step; flagged as containing opaque automation (`field_simp` + `linarith` + `exact_mod_cast`) so a reviewer should confirm denominator non-vanishing and ℤ→ℕ cast fidelity.",
                tactics_used=["have", "field_simp", "linarith", "exact_mod_cast", "zify", "rw", "exact"],
                referenced_lemmas=["ne_of_gt", "sq_abs"],
                confidence=0.79,
                opaque_automation=True,
                checks=[
                    FaithfulnessCheck(name="opaque_tactic_audit", status="warn", detail="Uses `field_simp`, `linarith`, and `exact_mod_cast`; intermediate algebraic normalization is implicit."),
                    FaithfulnessCheck(name="coercion_descent", status="pass", detail="Explicitly distinguishes ℝ → ℤ → ℕ cast steps."),
                ],
            ),
        },
        {
            "line_id": "sqrt2-L5",
            "section_label": "Evenness of |a|",
            "indent_level": 0,
            "lean_span": Span(start_line=24, end_line=25),
            "infotree_node_ids": ["n5"],
            "latex": r"\text{From } |a|^2 = 2b^2 \text{ we have } 2 \mid |a|^2\text{. Since } 2 \text{ is prime, Euclid's lemma yields } 2 \mid |a|.",
            "derivation": DerivationMeta(
                procedure=[
                    "Construct `h2_dvd_a_sq : 2 ∣ |a|^2` via anonymous existential witness `⟨b^2, hsq_nat⟩`.",
                    "Apply `Nat.Prime.dvd_of_dvd_pow` with `Nat.prime_two` to obtain `h2_dvd_a : 2 ∣ |a|`.",
                ],
                justification="Directly reflects the exact divisibility witness `b^2` and primality lemma `Nat.Prime.dvd_of_dvd_pow` in Lean's InfoTree.",
                tactics_used=["have"],
                referenced_lemmas=["Nat.Prime.dvd_of_dvd_pow", "Nat.prime_two"],
                confidence=0.96,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="lemma_citation", status="pass", detail="Primality of 2 (`Nat.prime_two`) explicitly cited."),
                    FaithfulnessCheck(name="divisibility_witness", status="pass", detail="Witness b² matches ⟨q.den^2, hsq_nat⟩."),
                ],
            ),
        },
        {
            "line_id": "sqrt2-L6",
            "section_label": "Substitution & Parity of b²",
            "indent_level": 0,
            "lean_span": Span(start_line=27, end_line=30),
            "infotree_node_ids": ["n6"],
            "latex": r"\text{Write } |a| = 2k \text{ for some } k \in \mathbb{N}\text{. Substituting into } |a|^2 = 2b^2 \text{ gives } 4k^2 = 2b^2\text{, hence } b^2 = 2k^2.",
            "derivation": DerivationMeta(
                procedure=[
                    "Destructure `h2_dvd_a` via `obtain ⟨k, hk⟩` introducing `k : ℕ` and `hk : |a| = 2 * k`.",
                    "Rewrite `hsq_nat` with `hk` to get `(2 * k)^2 = 2 * b^2`.",
                    "`linarith` cancels the factor of 2 to deduce `h2b_sq : b^2 = 2 * k^2`.",
                ],
                justification="Note that `(2k)^2 = 4k^2` and cancellation of the factor 2 are performed silently by `linarith` in Lean; our literal translation exposes `4k^2 = 2b^2` explicitly for mathematical clarity.",
                tactics_used=["obtain", "have", "rw", "linarith"],
                referenced_lemmas=[],
                confidence=0.81,
                opaque_automation=True,
                checks=[
                    FaithfulnessCheck(name="opaque_tactic_audit", status="warn", detail="`linarith` hides expansion `(2k)^2 = 4k^2` and division by 2 in ℕ."),
                    FaithfulnessCheck(name="binder_preservation", status="pass", detail="Existential k ∈ ℕ matches `obtain ⟨k, hk⟩`."),
                ],
            ),
        },
        {
            "line_id": "sqrt2-L7",
            "section_label": "Evenness of b",
            "indent_level": 0,
            "lean_span": Span(start_line=32, end_line=33),
            "infotree_node_ids": ["n7"],
            "latex": r"\text{Thus } 2 \mid b^2\text{ (witnessed by } k^2\text{), and again since } 2 \text{ is prime, } 2 \mid b.",
            "derivation": DerivationMeta(
                procedure=[
                    "Construct `h2_dvd_b_sq : 2 ∣ b^2` via `⟨k^2, h2b_sq⟩`.",
                    "Apply `Nat.Prime.dvd_of_dvd_pow Nat.prime_two h2_dvd_b_sq` to conclude `h2_dvd_b : 2 ∣ b`.",
                ],
                justification="Symmetric application of primality of 2 matching lines 32–33 verbatim.",
                tactics_used=["have"],
                referenced_lemmas=["Nat.Prime.dvd_of_dvd_pow", "Nat.prime_two"],
                confidence=0.96,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="lemma_citation", status="pass", detail="Matches `Nat.Prime.dvd_of_dvd_pow` symmetrically."),
                ],
            ),
        },
        {
            "line_id": "sqrt2-L8",
            "section_label": "Contradiction with Coprimality",
            "indent_level": 0,
            "lean_span": Span(start_line=35, end_line=37),
            "infotree_node_ids": ["n8"],
            "latex": r"\text{Since } 2 \mid |a| \text{ and } 2 \mid b\text{, we have } 2 \mid \gcd(|a|, b) = 1\text{, a contradiction. Therefore } \sqrt{2} \notin \mathbb{Q}.",
            "derivation": DerivationMeta(
                procedure=[
                    "Combine `h2_dvd_a` and `h2_dvd_b` via `Nat.dvd_gcd` to infer `2 ∣ Nat.gcd |a| b`.",
                    "Rewrite using `hcop.gcd_eq_one` to obtain `h2_dvd_gcd : 2 ∣ 1`.",
                    "`norm_num at h2_dvd_gcd` evaluates `2 ∣ 1` to `False`, discharging the contradiction goal.",
                ],
                justification="Closes the top-level contradiction introduced at line 7 (`intro ⟨q, hq⟩`). `norm_num` performs concrete arithmetic refutation of `2 ∣ 1`.",
                tactics_used=["have", "rw", "norm_num"],
                referenced_lemmas=["Nat.dvd_gcd", "Nat.Coprime.gcd_eq_one"],
                confidence=0.92,
                opaque_automation=True,
                checks=[
                    FaithfulnessCheck(name="goal_closure", status="pass", detail="goalsAfter is empty; proof closes ⊢ False."),
                    FaithfulnessCheck(name="opaque_tactic_audit", status="warn", detail="Final refutation of `2 ∣ 1` is discharged numerically by `norm_num`."),
                ],
            ),
        },
    ]

    expanded_overrides = {
        "sqrt2-L4": (
            r"\text{Since } b > 0 \text{ in } \mathbb{R}\text{, we have } b \neq 0\text{, so clearing the denominator in } \left(\frac{a}{b}\right)^2 = 2 \text{ gives } (a : \mathbb{R})^2 = 2(b : \mathbb{R})^2.\; \text{By injectivity of the ring homomorphism } \mathbb{Z} \hookrightarrow \mathbb{R},\; a^2 = 2b^2 \text{ in } \mathbb{Z}.\;\text{Finally, since } (|a| : \mathbb{Z})^2 = a^2 \text{ and } \mathbb{N} \hookrightarrow \mathbb{Z} \text{ is injective, } |a|^2 = 2b^2 \text{ holds in } \mathbb{N}.",
            [
                "Expanded `field_simp [ne_of_gt hb_pos]`: explicitly records `b ≠ 0` and algebraic clearing of `b²`.",
                "Expanded `exact_mod_cast`: states injectivity of `Int.cast : ℤ → ℝ`.",
                "Expanded `zify; rw [sq_abs]`: states injectivity of `Nat.cast : ℕ → ℤ` and `|a|² = a²`.",
            ],
            "Expanded automation mode unpacked `field_simp`, `linarith`, `exact_mod_cast`, and `zify` into explicit algebraic and cast-injectivity steps.",
        ),
        "sqrt2-L6": (
            r"\text{From } 2 \mid |a|\text{, choose } k \in \mathbb{N} \text{ with } |a| = 2k.\; \text{Substituting into } |a|^2 = 2b^2 \text{ yields } (2k)^2 = 4k^2 = 2b^2;\; \text{dividing both sides by } 2 > 0 \text{ yields } b^2 = 2k^2.",
            [
                "Expanded `obtain ⟨k, hk⟩` witness extraction.",
                "Expanded `linarith` arithmetic into explicit squaring `(2k)² = 4k²` and cancellation of factor `2 > 0`.",
            ],
            "Expanded automation mode makes the implicit `linarith` factor-of-2 cancellation explicit.",
        ),
    }

    prose_overrides = {
        "sqrt2-L1": (
            r"\text{Suppose toward a contradiction that } \sqrt{2} \text{ is rational, and let } q \in \mathbb{Q} \text{ satisfy } q = \sqrt{2}.",
            ["Rendered in formal mathematical prose while preserving witness `q ∈ ℚ`."],
            "Formal prose phrasing retaining the exact rational witness and contradiction structure.",
        ),
        "sqrt2-L4": (
            r"\text{Clearing denominators using } b > 0 \text{ and descending from } \mathbb{R} \text{ to } \mathbb{N} \text{ via } |a|^2 = a^2 \text{ yields the natural-number identity } |a|^2 = 2b^2.",
            ["Condensed cast sequence `field_simp` → `exact_mod_cast` → `zify` into structured mathematical prose."],
            "Formal prose style; note that intermediate coercion steps are summarized.",
        ),
    }

    return CuratedExample(
        key="irrational_sqrt_two",
        title="Irrationality of √2",
        subtitle="Classical coprime parity descent (Irrational (Real.sqrt 2))",
        difficulty="Foundational",
        infotree=infotree,
        literal_lines=literal_lines,
        expanded_overrides=expanded_overrides,
        prose_overrides=prose_overrides,
    )


def _build_harmonic_divergence() -> CuratedExample:
    src = _read_example_source("HarmonicDivergence.lean")

    def node(
        nid: str,
        start: int,
        end: int,
        tactic: str,
        before: GoalState,
        after: GoalState,
        refs: list[str],
        depth: int = 0,
        parent: str | None = None,
        opaque: bool = False,
    ) -> InfoTreeNode:
        return InfoTreeNode(
            node_id=nid,
            parent_id=parent,
            depth=depth,
            kind="tactic",
            tactic_kind=tactic,
            span=Span(start_line=start, end_line=end, start_col=1, end_col=80),
            source_slice=_slice_lines(src, start, end),
            goals_before=[before],
            goals_after=[after],
            referenced_constants=refs,
            is_opaque_automation=opaque,
        )

    h_n = Hypothesis(name="n", type="ℕ")
    h_ih = Hypothesis(name="ih", type="1 + (n : ℝ) / 2 ≤ harmonicSum (2 ^ n)", change="added")
    h_ih_u = Hypothesis(name="ih", type="1 + (n : ℝ) / 2 ≤ harmonicSum (2 ^ n)")
    h_split = Hypothesis(
        name="hsplit",
        type="harmonicSum (2 ^ (n + 1)) = harmonicSum (2 ^ n) + ∑ k ∈ Ioc (2 ^ n) (2 ^ (n + 1)), 1 / k",
        change="added",
    )
    h_split_u = Hypothesis(
        name="hsplit",
        type="harmonicSum (2 ^ (n + 1)) = harmonicSum (2 ^ n) + ∑ k ∈ Ioc (2 ^ n) (2 ^ (n + 1)), 1 / k",
    )
    h_term = Hypothesis(
        name="hterm",
        type="∀ k ∈ Ioc (2 ^ n) (2 ^ (n + 1)), 1 / (2 ^ (n + 1) : ℝ) ≤ 1 / (k : ℝ)",
        change="added",
    )
    h_term_u = Hypothesis(
        name="hterm",
        type="∀ k ∈ Ioc (2 ^ n) (2 ^ (n + 1)), 1 / (2 ^ (n + 1) : ℝ) ≤ 1 / (k : ℝ)",
    )
    h_block = Hypothesis(
        name="hblock",
        type="(1 : ℝ) / 2 ≤ ∑ k ∈ Ioc (2 ^ n) (2 ^ (n + 1)), (1 : ℝ) / (k : ℝ)",
        change="added",
    )
    h_block_u = Hypothesis(
        name="hblock",
        type="(1 : ℝ) / 2 ≤ ∑ k ∈ Ioc (2 ^ n) (2 ^ (n + 1)), (1 : ℝ) / (k : ℝ)",
    )
    h_M = Hypothesis(name="M", type="ℝ", change="added")
    h_M_u = Hypothesis(name="M", type="ℝ")
    h_n_ex = Hypothesis(name="n", type="ℕ", change="added")
    h_hn = Hypothesis(name="hn", type="2 * M < (n : ℝ)", change="added")
    h_ge = Hypothesis(name="hge", type="1 + (n : ℝ) / 2 ≤ harmonicSum (2 ^ n)", change="added")

    nodes = [
        node(
            "h1",
            8,
            9,
            "Lean.Parser.Command.definition",
            GoalState(tag="def", hypotheses=[Hypothesis(name="N", type="ℕ")], target="ℝ"),
            GoalState(tag="def", hypotheses=[Hypothesis(name="N", type="ℕ")], target="harmonicSum N := ∑ k ∈ Icc 1 N, 1 / k"),
            ["Finset.Icc", "Finset.sum"],
        ),
        node(
            "h2",
            14,
            17,
            "Lean.Parser.Tactic.induction",
            GoalState(tag="zero", hypotheses=[], target="1 + (0 : ℝ) / 2 ≤ harmonicSum (2 ^ 0)"),
            GoalState(tag="zero", hypotheses=[], target="Goals accomplished (case zero)"),
            ["induction", "simp", "harmonicSum"],
            depth=1,
            opaque=True,
        ),
        node(
            "h3",
            18,
            23,
            "Lean.Parser.Tactic.rwSeq",
            GoalState(tag="succ", hypotheses=[h_n, h_ih], target="1 + ((n + 1 : ℕ) : ℝ) / 2 ≤ harmonicSum (2 ^ (n + 1))"),
            GoalState(tag="succ", hypotheses=[h_n, h_ih_u, h_split], target="1 + ((n + 1 : ℕ) : ℝ) / 2 ≤ harmonicSum (2 ^ (n + 1))"),
            ["Finset.sum_Icc_add_sum_Ioc", "Nat.pow_le_pow_right", "Nat.le_succ"],
            depth=1,
        ),
        node(
            "h4",
            25,
            32,
            "Lean.Parser.Tactic.exact",
            GoalState(tag="succ", hypotheses=[h_n, h_ih_u, h_split_u], target="1 + ((n + 1 : ℕ) : ℝ) / 2 ≤ harmonicSum (2 ^ (n + 1))"),
            GoalState(tag="succ", hypotheses=[h_n, h_ih_u, h_split_u, h_term], target="1 + ((n + 1 : ℕ) : ℝ) / 2 ≤ harmonicSum (2 ^ (n + 1))"),
            ["Finset.mem_Ioc", "one_div_le_one_div_of_le", "exact_mod_cast"],
            depth=2,
        ),
        node(
            "h5",
            34,
            37,
            "Lean.Elab.Tactic.Omega.omega",
            GoalState(tag="succ.hcard", hypotheses=[h_n], target="(Finset.Ioc (2 ^ n) (2 ^ (n + 1))).card = 2 ^ n"),
            GoalState(tag="succ.hcard", hypotheses=[h_n, Hypothesis(name="hcard", type="(Ioc (2^n) (2^(n+1))).card = 2^n", change="added")], target="Goals accomplished (hcard)"),
            ["Nat.card_Ioc", "pow_succ", "omega"],
            depth=2,
            opaque=True,
        ),
        node(
            "h6",
            38,
            44,
            "Lean.Parser.Tactic.calc",
            GoalState(tag="succ.hblock", hypotheses=[h_n, h_term_u], target="(1 : ℝ) / 2 ≤ ∑ k ∈ Ioc (2 ^ n) (2 ^ (n + 1)), 1 / k"),
            GoalState(tag="succ", hypotheses=[h_n, h_ih_u, h_split_u, h_term_u, h_block], target="1 + ((n + 1 : ℕ) : ℝ) / 2 ≤ harmonicSum (2 ^ (n + 1))"),
            ["pow_succ", "field_simp", "Finset.sum_const", "nsmul_eq_mul", "Finset.sum_le_sum"],
            depth=2,
        ),
        node(
            "h7",
            46,
            48,
            "Mathlib.Tactic.Linarith.linarith",
            GoalState(tag="succ", hypotheses=[h_n, h_ih_u, h_split_u, h_block_u], target="1 + ((n + 1 : ℕ) : ℝ) / 2 ≤ harmonicSum (2 ^ (n + 1))"),
            GoalState(tag="succ", hypotheses=[h_n, h_ih_u, h_split_u, h_block_u], target="Goals accomplished (lemma harmonicSum_two_pow_ge)"),
            ["rw", "push_cast", "linarith"],
            depth=1,
            opaque=True,
        ),
        node(
            "h8",
            51,
            54,
            "Lean.Parser.Tactic.refine",
            GoalState(tag="main", hypotheses=[], target="∀ M : ℝ, ∃ N : ℕ, M < harmonicSum N"),
            GoalState(tag="main", hypotheses=[h_M, h_n_ex, h_hn], target="M < harmonicSum (2 ^ n)"),
            ["intro", "exists_nat_gt", "refine"],
        ),
        node(
            "h9",
            55,
            56,
            "Mathlib.Tactic.Linarith.linarith",
            GoalState(tag="main", hypotheses=[h_M_u, h_n_ex, h_hn], target="M < harmonicSum (2 ^ n)"),
            GoalState(tag="main", hypotheses=[h_M_u, h_n_ex, h_hn, h_ge], target="Goals accomplished ⊢ ∀ M, ∃ N, M < H_N"),
            ["harmonicSum_two_pow_ge", "linarith"],
            opaque=True,
        ),
    ]

    infotree = InfoTreeDocument(
        theorem_name="harmonic_series_diverges",
        statement_lean="theorem harmonic_series_diverges : ∀ M : ℝ, ∃ N : ℕ, M < harmonicSum N",
        statement_latex=r"\forall M \in \mathbb{R},\; \exists N \in \mathbb{N},\; \sum_{k=1}^{N} \frac{1}{k} > M",
        source_code=src,
        lean_version="4.12.0",
        extractor_mode="precomputed_infotree",
        nodes=nodes,
    )

    literal_lines = [
        {
            "line_id": "harm-L1",
            "section_label": "Partial Sum Definition",
            "indent_level": 0,
            "lean_span": Span(start_line=8, end_line=9),
            "infotree_node_ids": ["h1"],
            "latex": r"\text{For } N \in \mathbb{N}\text{, define the } N\text{-th harmonic partial sum } H_N := \sum_{k=1}^{N} \frac{1}{k} \in \mathbb{R}.",
            "derivation": DerivationMeta(
                procedure=[
                    "Extract definition `harmonicSum (N : ℕ) : ℝ`.",
                    "Translate `∑ k ∈ Finset.Icc 1 N, (1 : ℝ) / (k : ℝ)` over closed integer interval `[1, N]` into ∑_{k=1}^N 1/k.",
                ],
                justification="Exact notation mapping from `Finset.Icc 1 N` to summation limits `k=1` to `N`.",
                tactics_used=["def"],
                referenced_lemmas=["Finset.Icc"],
                confidence=0.98,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="domain_bounds", status="pass", detail="Finset.Icc 1 N equals {1, …, N} (empty when N=0)."),
                ],
            ),
        },
        {
            "line_id": "harm-L2",
            "section_label": "Oresme Lemma — Base Case (n = 0)",
            "indent_level": 0,
            "lean_span": Span(start_line=12, end_line=17),
            "infotree_node_ids": ["h2"],
            "latex": r"\textbf{Lemma (Dyadic Lower Bound).}\; \text{We prove } 1 + \frac{n}{2} \le H_{2^n} \text{ by induction on } n \in \mathbb{N}.\;\text{For } n = 0,\; 1 + \frac{0}{2} = 1 = H_{2^0}.",
            "derivation": DerivationMeta(
                procedure=[
                    "Identify lemma target `1 + (n : ℝ) / 2 ≤ harmonicSum (2 ^ n)` and `induction n`.",
                    "Branch `| zero => simp [harmonicSum]` simplifies `2^0 = 1`, `Icc 1 1 = {1}`, and `1 + 0/2 ≤ 1`.",
                ],
                justification="`simp [harmonicSum]` discharges the base case by unfolding the singleton sum `H_1 = 1` and arithmetic simplification.",
                tactics_used=["induction", "simp"],
                referenced_lemmas=["harmonicSum"],
                confidence=0.88,
                opaque_automation=True,
                checks=[
                    FaithfulnessCheck(name="opaque_tactic_audit", status="warn", detail="`simp [harmonicSum]` folds `2^0 = 1`, `Finset.Icc 1 1 = {1}`, and `0/2 = 0` automatically."),
                    FaithfulnessCheck(name="induction_scheme", status="pass", detail="Standard ℕ induction (`zero` / `succ`)."),
                ],
            ),
        },
        {
            "line_id": "harm-L3",
            "section_label": "Inductive Step — Dyadic Block Decomposition",
            "indent_level": 1,
            "lean_span": Span(start_line=18, end_line=23),
            "infotree_node_ids": ["h3"],
            "latex": r"\text{Assume } 1 + \frac{n}{2} \le H_{2^n}.\;\text{Since } 2^n \le 2^{n+1}\text{, splitting the index interval } [1, 2^{n+1}] = [1, 2^n] \sqcup (2^n, 2^{n+1}] \text{ yields } H_{2^{n+1}} = H_{2^n} + \sum_{k = 2^n + 1}^{2^{n+1}} \frac{1}{k}.",
            "derivation": DerivationMeta(
                procedure=[
                    "Introduce inductive hypothesis `ih : 1 + n/2 ≤ harmonicSum (2^n)` from `| succ n ih =>`.",
                    "Apply `Finset.sum_Icc_add_sum_Ioc` justified by monotonicity `2^n ≤ 2^(n+1)` (`Nat.pow_le_pow_right`).",
                    "Translate half-open interval `Finset.Ioc (2^n) (2^(n+1))` to integer range `k = 2^n + 1` to `2^(n+1)`.",
                ],
                justification="Literally preserves the interval partition lemma and its monotonicity precondition `2^n ≤ 2^(n+1)`.",
                tactics_used=["have", "unfold", "rw"],
                referenced_lemmas=["Finset.sum_Icc_add_sum_Ioc", "Nat.pow_le_pow_right", "Nat.le_succ"],
                confidence=0.95,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="interval_endpoints", status="pass", detail="Half-open `Ioc (2^n) (2^(n+1))` accurately translated as k = 2^n + 1 .. 2^(n+1)."),
                ],
            ),
        },
        {
            "line_id": "harm-L4",
            "section_label": "Termwise Lower Bound on Dyadic Block",
            "indent_level": 1,
            "lean_span": Span(start_line=25, end_line=32),
            "infotree_node_ids": ["h4"],
            "latex": r"\text{For every } k \in (2^n, 2^{n+1}] \cap \mathbb{N}\text{, we have } 0 < k \le 2^{n+1}\text{, so reciprocal antitonicity gives } \frac{1}{2^{n+1}} \le \frac{1}{k}.",
            "derivation": DerivationMeta(
                procedure=[
                    "Introduce `k` and membership `hk : k ∈ Finset.Ioc (2^n) (2^(n+1))`.",
                    "Derive positivity `0 < (k : ℝ)` from `0 ≤ 2^n < k` and upper bound `(k : ℝ) ≤ 2^(n+1)` via `exact_mod_cast`.",
                    "Apply `one_div_le_one_div_of_le hk_pos hk_le`.",
                ],
                justification="Explicitly preserves the strict positivity premise `0 < k` required for order reversal of `x ↦ 1/x`.",
                tactics_used=["have", "intro", "exact_mod_cast", "exact"],
                referenced_lemmas=["Finset.mem_Ioc", "one_div_le_one_div_of_le"],
                confidence=0.96,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="positivity_guard", status="pass", detail="Positivity `0 < k` retained from `hk_pos`."),
                    FaithfulnessCheck(name="quantifier_scope", status="pass", detail="Universal binder `∀ k ∈ (2^n, 2^(n+1)]` preserved."),
                ],
            ),
        },
        {
            "line_id": "harm-L5",
            "section_label": "Dyadic Block Cardinality",
            "indent_level": 1,
            "lean_span": Span(start_line=34, end_line=37),
            "infotree_node_ids": ["h5"],
            "latex": r"\text{The dyadic block } (2^n, 2^{n+1}] \cap \mathbb{N} \text{ has cardinality } 2^{n+1} - 2^n = 2^n.",
            "derivation": DerivationMeta(
                procedure=[
                    "Rewrite cardinality with `Nat.card_Ioc` giving `2^(n+1) - 2^n`.",
                    "Rewrite `2^(n+1) = 2^n * 2` via `pow_succ` and close subtraction in ℕ with `omega`.",
                ],
                justification="Note that Lean's subtraction on `ℕ` is truncated subtraction; `omega` implicitly verifies `2^n ≤ 2^(n+1)` so `2^(n+1) - 2^n = 2^n` is exact.",
                tactics_used=["have", "rw", "omega"],
                referenced_lemmas=["Nat.card_Ioc", "pow_succ"],
                confidence=0.83,
                opaque_automation=True,
                checks=[
                    FaithfulnessCheck(name="opaque_tactic_audit", status="warn", detail="`omega` proves `2^n * 2 - 2^n = 2^n` in truncated ℕ arithmetic without displaying intermediate factoring."),
                ],
            ),
        },
        {
            "line_id": "harm-L6",
            "section_label": "Block Sum Lower Bound (calc Chain)",
            "indent_level": 1,
            "lean_span": Span(start_line=38, end_line=44),
            "infotree_node_ids": ["h6"],
            "latex": r"\frac{1}{2} = 2^n \cdot \frac{1}{2^{n+1}} = \sum_{k = 2^n + 1}^{2^{n+1}} \frac{1}{2^{n+1}} \le \sum_{k = 2^n + 1}^{2^{n+1}} \frac{1}{k}.",
            "derivation": DerivationMeta(
                procedure=[
                    "Map 3-step `calc` block verbatim to a chain of two equalities and one inequality.",
                    "Step 1 (`rw [pow_succ]; field_simp`): `1/2 = 2^n * (1 / 2^(n+1))`.",
                    "Step 2 (`Finset.sum_const`, `nsmul_eq_mul`, `hcard`): constant sum over `2^n` terms.",
                    "Step 3 (`Finset.sum_le_sum hterm`): monotone summation of the pointwise bound `hterm`.",
                ],
                justification="Direct 1-to-1 rendering of Lean's `calc` chain; every relation symbol (`=`, `=`, `≤`) matches the elaborated `calc` steps.",
                tactics_used=["calc", "rw", "field_simp"],
                referenced_lemmas=["pow_succ", "Finset.sum_const", "nsmul_eq_mul", "Finset.sum_le_sum"],
                confidence=0.94,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="calc_chain_order", status="pass", detail="Exact 4-term `calc` relation chain preserved."),
                ],
            ),
        },
        {
            "line_id": "harm-L7",
            "section_label": "Closing the Inductive Step",
            "indent_level": 1,
            "lean_span": Span(start_line=46, end_line=48),
            "infotree_node_ids": ["h7"],
            "latex": r"\text{Combining the inductive hypothesis and block bound gives } H_{2^{n+1}} = H_{2^n} + \sum_{k=2^n+1}^{2^{n+1}} \frac{1}{k} \ge \left(1 + \frac{n}{2}\right) + \frac{1}{2} = 1 + \frac{n+1}{2}.",
            "derivation": DerivationMeta(
                procedure=[
                    "Substitute `hsplit` into the inductive goal (`rw [hsplit]`).",
                    "Normalize natural-to-real cast `((n + 1 : ℕ) : ℝ) = (n : ℝ) + 1` via `push_cast`.",
                    "Combine `ih` and `hblock` via `linarith`.",
                ],
                justification="Exposes the exact linear combination `(1 + n/2) + 1/2 = 1 + (n+1)/2` compressed inside `linarith`.",
                tactics_used=["rw", "push_cast", "linarith"],
                referenced_lemmas=[],
                confidence=0.84,
                opaque_automation=True,
                checks=[
                    FaithfulnessCheck(name="opaque_tactic_audit", status="warn", detail="`linarith` combines `ih` and `hblock` and simplifies `(n + 1)/2 = n/2 + 1/2` automatically."),
                ],
            ),
        },
        {
            "line_id": "harm-L8",
            "section_label": "Unboundedness — Choosing N = 2ⁿ",
            "indent_level": 0,
            "lean_span": Span(start_line=51, end_line=54),
            "infotree_node_ids": ["h8"],
            "latex": r"\textbf{Proof of Divergence.}\; \text{Let } M \in \mathbb{R}\text{. By the Archimedean property, choose } n \in \mathbb{N} \text{ with } 2M < n\text{, and set } N := 2^n.",
            "derivation": DerivationMeta(
                procedure=[
                    "`intro M` introduces an arbitrary real bound `M : ℝ`.",
                    "`obtain ⟨n, hn⟩ := exists_nat_gt (2 * M)` extracts `n : ℕ` satisfying `2 * M < (n : ℝ)`.",
                    "`refine ⟨2 ^ n, ?_⟩` instantiates the existential witness `N := 2^n`.",
                ],
                justification="Exact witness mapping for the ∀–∃ quantifier alternation; `exists_nat_gt` is Mathlib's Archimedean existence lemma.",
                tactics_used=["intro", "obtain", "refine"],
                referenced_lemmas=["exists_nat_gt"],
                confidence=0.97,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="quantifier_binding", status="pass", detail="∀ M ∈ ℝ, ∃ N ∈ ℕ with N = 2^n matches InfoTree exactly."),
                ],
            ),
        },
        {
            "line_id": "harm-L9",
            "section_label": "Final Inequality",
            "indent_level": 0,
            "lean_span": Span(start_line=55, end_line=56),
            "infotree_node_ids": ["h9"],
            "latex": r"\text{By the dyadic lower bound, } M < \frac{n}{2} < 1 + \frac{n}{2} \le H_{2^n} = H_N\text{. Hence the harmonic series diverges.}",
            "derivation": DerivationMeta(
                procedure=[
                    "Instantiate `hge := harmonicSum_two_pow_ge n` (`1 + n/2 ≤ H_{2^n}`).",
                    "`linarith` combines `2 * M < n` and `1 + n/2 ≤ H_{2^n}` to conclude `M < H_{2^n}`.",
                ],
                justification="Unpacks the strict inequality chain `M < n/2 < 1 + n/2 ≤ H_{2^n}` implied by `hn` and `hge` inside `linarith`.",
                tactics_used=["have", "linarith"],
                referenced_lemmas=["harmonicSum_two_pow_ge"],
                confidence=0.86,
                opaque_automation=True,
                checks=[
                    FaithfulnessCheck(name="opaque_tactic_audit", status="warn", detail="`linarith` combines `2M < n` and `1 + n/2 ≤ H_{2^n}` into `M < H_{2^n}`."),
                    FaithfulnessCheck(name="goal_closure", status="pass", detail="Main theorem goal closed cleanly."),
                ],
            ),
        },
    ]

    expanded_overrides = {
        "harm-L2": (
            r"\textbf{Lemma.}\; \text{We prove } 1 + \frac{n}{2} \le H_{2^n} \text{ by induction on } n \in \mathbb{N}.\;\text{Base case } n = 0:\; 2^0 = 1\text{, so } H_{2^0} = \sum_{k \in \{1\}} \frac{1}{k} = 1 = 1 + \frac{0}{2}.",
            [
                "Expanded `simp [harmonicSum]` into explicit evaluation `2^0 = 1`, `Icc 1 1 = {1}`, `1/1 = 1`, and `0/2 = 0`.",
            ],
            "Expanded automation mode unpacks `simp [harmonicSum]` into explicit arithmetic identities.",
        ),
        "harm-L5": (
            r"\text{Since } 2^n \le 2^{n+1} = 2 \cdot 2^n\text{, the number of integers in } (2^n, 2^{n+1}] \text{ is } 2^{n+1} - 2^n = 2 \cdot 2^n - 2^n = 2^n.",
            [
                "Expanded `omega` by noting `2^n ≤ 2^(n+1)` prevents ℕ-subtraction truncation and factoring `2·2^n - 2^n = 2^n`.",
            ],
            "Expanded automation mode makes `omega`'s truncated-subtraction safety check explicit.",
        ),
    }

    prose_overrides = {
        "harm-L6": (
            r"\text{Summing the constant lower bound } \frac{1}{2^{n+1}} \text{ across all } 2^n \text{ terms of the dyadic block shows that the block contributes at least } \frac{1}{2}.",
            ["Summarized 3-step `calc` inequality chain into concise prose."],
            "Formal prose style; switches from displayed equation chain to narrative sentence.",
        ),
    }

    return CuratedExample(
        key="harmonic_series_diverges",
        title="Divergence of the Harmonic Series",
        subtitle="Oresme's dyadic block lower bound H_{2^n} ≥ 1 + n/2",
        difficulty="Analysis / Induction",
        infotree=infotree,
        literal_lines=literal_lines,
        expanded_overrides=expanded_overrides,
        prose_overrides=prose_overrides,
    )


def _build_infinitude_of_primes() -> CuratedExample:
    src = _read_example_source("InfinitudeOfPrimes.lean")

    def node(
        nid: str,
        start: int,
        end: int,
        tactic: str,
        before: GoalState,
        after: GoalState,
        refs: list[str],
        depth: int = 0,
        opaque: bool = False,
    ) -> InfoTreeNode:
        return InfoTreeNode(
            node_id=nid,
            depth=depth,
            kind="tactic",
            tactic_kind=tactic,
            span=Span(start_line=start, end_line=end, start_col=1, end_col=80),
            source_slice=_slice_lines(src, start, end),
            goals_before=[before],
            goals_after=[after],
            referenced_constants=refs,
            is_opaque_automation=opaque,
        )

    h_n = Hypothesis(name="n", type="ℕ")
    h_p = Hypothesis(name="p", type="ℕ := Nat.minFac (n! + 1)", change="added")
    h_p_u = Hypothesis(name="p", type="ℕ := Nat.minFac (n! + 1)")
    h_ne = Hypothesis(name="hne", type="n! + 1 ≠ 1", change="added")
    h_prime = Hypothesis(name="hp_prime", type="Nat.Prime p", change="added")
    h_prime_u = Hypothesis(name="hp_prime", type="Nat.Prime p")
    h_hlt = Hypothesis(name="hlt", type="p < n", change="added")
    h_hlt_u = Hypothesis(name="hlt", type="p < n")
    h_dfac = Hypothesis(name="hp_dvd_fac", type="p ∣ n!", change="added")
    h_dsucc = Hypothesis(name="hp_dvd_succ", type="p ∣ n! + 1", change="added")
    h_done = Hypothesis(name="hp_dvd_one", type="p ∣ 1", change="added")
    h_ge = Hypothesis(name="hge", type="n ≤ p", change="added")

    nodes = [
        node(
            "p1",
            8,
            11,
            "Lean.Elab.Tactic.Omega.omega",
            GoalState(tag="main", hypotheses=[h_n], target="∃ p, n ≤ p ∧ Nat.Prime p"),
            GoalState(tag="main", hypotheses=[h_n, h_p, h_ne], target="∃ p, n ≤ p ∧ Nat.Prime p"),
            ["Nat.minFac", "Nat.factorial_pos", "omega"],
            opaque=True,
        ),
        node(
            "p2",
            13,
            13,
            "Lean.Parser.Tactic.have",
            GoalState(tag="main", hypotheses=[h_n, h_p_u, h_ne], target="∃ p, n ≤ p ∧ Nat.Prime p"),
            GoalState(tag="main", hypotheses=[h_n, h_p_u, h_prime], target="∃ p, n ≤ p ∧ Nat.Prime p"),
            ["Nat.minFac_prime"],
        ),
        node(
            "p3",
            15,
            17,
            "Mathlib.Tactic.PushNeg.pushNeg",
            GoalState(tag="hge", hypotheses=[h_n, h_p_u, h_prime_u], target="n ≤ p"),
            GoalState(tag="hge", hypotheses=[h_n, h_p_u, h_prime_u, h_hlt], target="False"),
            ["by_contra", "push_neg"],
            depth=1,
        ),
        node(
            "p4",
            18,
            20,
            "Lean.Parser.Tactic.have",
            GoalState(tag="hge", hypotheses=[h_n, h_p_u, h_prime_u, h_hlt_u], target="False"),
            GoalState(tag="hge", hypotheses=[h_n, h_p_u, h_prime_u, h_hlt_u, h_dfac, h_dsucc], target="False"),
            ["Nat.dvd_factorial", "Nat.Prime.pos", "le_of_lt", "Nat.minFac_dvd"],
            depth=1,
        ),
        node(
            "p5",
            21,
            23,
            "Lean.Parser.Tactic.exact",
            GoalState(tag="hge", hypotheses=[h_n, h_p_u, h_prime_u, h_dfac, h_dsucc], target="False"),
            GoalState(tag="main", hypotheses=[h_n, h_p_u, h_prime_u, h_done, h_ge], target="Goals accomplished"),
            ["Nat.dvd_add_right", "Nat.Prime.not_dvd_one"],
        ),
    ]

    infotree = InfoTreeDocument(
        theorem_name="exists_infinite_primes",
        statement_lean="theorem exists_infinite_primes (n : ℕ) : ∃ p, n ≤ p ∧ Nat.Prime p",
        statement_latex=r"\forall n \in \mathbb{N},\; \exists p \in \mathbb{N},\; n \le p \land \mathrm{Prime}(p)",
        source_code=src,
        lean_version="4.12.0",
        extractor_mode="precomputed_infotree",
        nodes=nodes,
    )

    literal_lines = [
        {
            "line_id": "prime-L1",
            "section_label": "Factorial Construction",
            "indent_level": 0,
            "lean_span": Span(start_line=8, end_line=11),
            "infotree_node_ids": ["p1"],
            "latex": r"\text{Let } p := \mathrm{minFac}(n! + 1) \text{ denote the smallest nontrivial factor of } n! + 1.\;\text{Since } n! > 0\text{, we have } n! + 1 \neq 1.",
            "derivation": DerivationMeta(
                procedure=[
                    "Bind local definition `p := Nat.minFac (n! + 1)`.",
                    "Record `hpos : 0 < n!` via `Nat.factorial_pos n` and close `n! + 1 ≠ 1` with `omega`.",
                ],
                justification="Direct correspondence with Euclid's factorial witness and non-unit precondition required by `Nat.minFac_prime`.",
                tactics_used=["let", "have", "omega"],
                referenced_lemmas=["Nat.minFac", "Nat.factorial_pos"],
                confidence=0.91,
                opaque_automation=True,
                checks=[
                    FaithfulnessCheck(name="opaque_tactic_audit", status="warn", detail="`omega` derives `n! + 1 ≠ 1` from `0 < n!`."),
                ],
            ),
        },
        {
            "line_id": "prime-L2",
            "section_label": "Primality of p",
            "indent_level": 0,
            "lean_span": Span(start_line=13, end_line=13),
            "infotree_node_ids": ["p2"],
            "latex": r"\text{Because } n! + 1 \neq 1\text{, its least factor } p \text{ is prime.}",
            "derivation": DerivationMeta(
                procedure=["Apply `Nat.minFac_prime hne` to conclude `hp_prime : Nat.Prime p`."],
                justification="Single-lemma application establishing primality of `p`.",
                tactics_used=["have"],
                referenced_lemmas=["Nat.minFac_prime"],
                confidence=0.98,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="lemma_citation", status="pass", detail="Exact match to `Nat.minFac_prime`."),
                ],
            ),
        },
        {
            "line_id": "prime-L3",
            "section_label": "Lower Bound by Contradiction",
            "indent_level": 1,
            "lean_span": Span(start_line=15, end_line=17),
            "infotree_node_ids": ["p3"],
            "latex": r"\text{To prove } n \le p\text{, assume for contradiction that } p < n.",
            "derivation": DerivationMeta(
                procedure=[
                    "`by_contra hlt` assumes `¬ (n ≤ p)`.",
                    "`push_neg at hlt` normalizes `¬ (n ≤ p)` to `hlt : p < n`.",
                ],
                justification="Literal rendering of classical negation + `push_neg` normalization.",
                tactics_used=["have", "by_contra", "push_neg"],
                referenced_lemmas=[],
                confidence=0.97,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="goal_polarity", status="pass", detail="Strict inequality `p < n` matches `push_neg` output."),
                ],
            ),
        },
        {
            "line_id": "prime-L4",
            "section_label": "Common Divisibility",
            "indent_level": 1,
            "lean_span": Span(start_line=18, end_line=20),
            "infotree_node_ids": ["p4"],
            "latex": r"\text{Since } 0 < p \le n\text{, we have } p \mid n!\text{. By definition of } \mathrm{minFac}\text{, we also have } p \mid (n! + 1).",
            "derivation": DerivationMeta(
                procedure=[
                    "`Nat.dvd_factorial hp_prime.pos (le_of_lt hlt)` derives `p ∣ n!`.",
                    "`Nat.minFac_dvd _` gives `p ∣ n! + 1`.",
                ],
                justification="Explicitly retains `0 < p` (`hp_prime.pos`) and `p ≤ n` (`le_of_lt hlt`) required by `Nat.dvd_factorial`.",
                tactics_used=["have"],
                referenced_lemmas=["Nat.dvd_factorial", "Nat.Prime.pos", "le_of_lt", "Nat.minFac_dvd"],
                confidence=0.96,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="hypothesis_coverage", status="pass", detail="Both `0 < p` and `p ≤ n` preserved."),
                ],
            ),
        },
        {
            "line_id": "prime-L5",
            "section_label": "Contradiction & Witness Conclusion",
            "indent_level": 0,
            "lean_span": Span(start_line=21, end_line=23),
            "infotree_node_ids": ["p5"],
            "latex": r"\text{Hence } p \mid 1\text{, contradicting the primality of } p\text{. Therefore } n \le p \text{ and } p \text{ is prime, completing the proof.}",
            "derivation": DerivationMeta(
                procedure=[
                    "`(Nat.dvd_add_right hp_dvd_fac).mp hp_dvd_succ` cancels `n!` to yield `hp_dvd_one : p ∣ 1`.",
                    "`hp_prime.not_dvd_one hp_dvd_one` closes the contradiction subgoal `hge : n ≤ p`.",
                    "`exact ⟨p, hge, hp_prime⟩` witnesses the existential conclusion.",
                ],
                justification="Exact closure of both the inner contradiction and outer existential witness `⟨p, hge, hp_prime⟩`.",
                tactics_used=["have", "exact"],
                referenced_lemmas=["Nat.dvd_add_right", "Nat.Prime.not_dvd_one"],
                confidence=0.97,
                opaque_automation=False,
                checks=[
                    FaithfulnessCheck(name="goal_closure", status="pass", detail="Witness ⟨p, hge, hp_prime⟩ discharges theorem."),
                ],
            ),
        },
    ]

    return CuratedExample(
        key="exists_infinite_primes",
        title="Infinitude of Primes",
        subtitle="Euclid's factorial construction (exists_infinite_primes)",
        difficulty="Number Theory",
        infotree=infotree,
        literal_lines=literal_lines,
        expanded_overrides={},
        prose_overrides={},
    )


_EXAMPLES_CACHE: dict[str, CuratedExample] | None = None


def get_curated_examples() -> dict[str, CuratedExample]:
    global _EXAMPLES_CACHE
    if _EXAMPLES_CACHE is None:
        examples = [
            _build_irrational_sqrt_two(),
            _build_harmonic_divergence(),
            _build_infinitude_of_primes(),
        ]
        _EXAMPLES_CACHE = {ex.key: ex for ex in examples}
    return _EXAMPLES_CACHE


def list_example_summaries() -> list[ExampleSummary]:
    return [
        ExampleSummary(
            key=ex.key,
            title=ex.title,
            subtitle=ex.subtitle,
            theorem_name=ex.infotree.theorem_name,
            difficulty=ex.difficulty,
            line_count=len(ex.literal_lines),
            statement_latex=ex.infotree.statement_latex,
        )
        for ex in get_curated_examples().values()
    ]


def build_lines_from_curated(
    example: CuratedExample,
    fidelity_mode: FidelityMode = FidelityMode.LITERAL,
) -> list[ProofLine]:
    result: list[ProofLine] = []
    for idx, item in enumerate(example.literal_lines, start=1):
        line_id = item["line_id"]
        latex = item["latex"]
        deriv: DerivationMeta = item["derivation"].model_copy(deep=True)
        deriv.fidelity_mode = fidelity_mode

        if fidelity_mode == FidelityMode.EXPANDED and line_id in example.expanded_overrides:
            latex, extra_proc, new_just = example.expanded_overrides[line_id]
            deriv.procedure = deriv.procedure + extra_proc
            deriv.justification = new_just
            deriv.confidence = min(0.96, round(deriv.confidence + 0.06, 2))
        elif fidelity_mode == FidelityMode.FORMAL_PROSE and line_id in example.prose_overrides:
            latex, new_proc, new_just = example.prose_overrides[line_id]
            deriv.procedure = new_proc
            deriv.justification = new_just

        result.append(
            ProofLine(
                line_id=line_id,
                line_number=idx,
                section_label=item["section_label"],
                indent_level=item["indent_level"],
                latex=latex,
                original_latex=latex,
                lean_span=item["lean_span"],
                infotree_node_ids=item["infotree_node_ids"],
                status=LineStatus.UNREVIEWED,
                derivation=deriv,
                flags=[],
                revisions=[
                    LineRevision(
                        revision_index=0,
                        latex=latex,
                        source="initial_inference",
                        model_id=deriv.model_id,
                        fidelity_mode=fidelity_mode,
                        justification=deriv.justification,
                    )
                ],
            )
        )
    return result
