from __future__ import annotations

from lit_core.extractor import extract_infotree_heuristic
from lit_core.latex_fmt import (
    escape_latex_code,
    escape_latex_text,
    lean_expr_to_latex,
    strip_lean_comments_preserving_lines,
    validate_katex_safety,
)
from lit_core.schemas import FidelityMode
from lit_core.translator import _translate_single_node_symbolic


def test_strip_lean_comments_preserves_lines_and_handles_nesting() -> None:
    src = (
        "/- outer comment\n"
        "   /- nested comment -/\n"
        "   still inside comment -/\n"
        "def s_p (p n : ℕ) : ℕ := n -- trailing comment\n"
        'let msg := "keep /- literal -/ and -- text"\n'
        "/- unclosed at EOF\n"
        "should be stripped safely"
    )
    stripped = strip_lean_comments_preserving_lines(src)
    assert len(stripped.splitlines()) == len(src.splitlines())
    lines = stripped.splitlines()
    assert lines[0].strip() == ""
    assert lines[1].strip() == ""
    assert lines[2].strip() == ""
    assert lines[3].strip() == "def s_p (p n : ℕ) : ℕ := n"
    assert '"keep /- literal -/ and -- text"' in lines[4]
    assert lines[5].strip() == ""
    assert lines[6].strip() == ""


def test_escape_latex_text_and_code_prevent_katex_failures() -> None:
    raw = r"rw [← h_legendre, m % p ^ 2, {x₀}, \ S, $1, #a, &b, ~c, ‹_›, ∀ᶠ x, ⌊x⌋₊]"
    escaped = escape_latex_code(raw, max_len=200)
    tex = rf"\texttt{{{escaped}}}"
    assert validate_katex_safety(tex) == []
    assert r"\_" in tex
    assert r"\%" in tex
    assert r"\^{}" in tex
    assert r"\{" in tex and r"\}" in tex
    # Ensure non-ASCII chars were transliterated out of text mode
    assert all(ord(ch) <= 127 for ch in escaped)

    # Truncation safety on very long slice
    long_code = "exact " + "a_1 + " * 80
    trunc = escape_latex_code(long_code, max_len=80)
    assert len(trunc) <= 140
    assert trunc.endswith("...")
    assert validate_katex_safety(rf"\texttt{{{trunc}}}") == []


def test_lean_expr_to_latex_adversarial_constructs() -> None:
    cases = [
        "h_multiples_j_v_le",
        "Nat.mul_le_mul_right _ (Nat.digit_sum_le _ _)",
        "(m % p ^ (k + 1)) ≥ p ^ (k + 1)",
        "Finset.univ \\ {x₀}",
        "∀ᶠ x in Filter.atTop, (f x : ℝ) =o[Filter.atTop] (fun x => x)",
        "m ≡ s_p p m [MOD (p - 1)]",
        "⌊1 + Real.log x / Real.log p⌋₊ ^ B",
        "x ^ (1 - 1 / (5 * Real.log p))",
        "f' ^ 2 ^ 3",
        "x⁻¹ ^ 2",
        "‹∀ x : ℝ, 3 ≤ x → x ≥ 0›",
        "Nat.digits p m |> List.length",
        "p ^ (i + 1) ≤",  # truncated at EOF near ^
    ]
    for expr in cases:
        out = lean_expr_to_latex(expr)
        assert validate_katex_safety(out) == [], f"Safety issues on {expr!r}: {out!r}"
        assert out.strip() != ""


def test_multi_theorem_def_bullet_and_tactic_extraction() -> None:
    lean = """
/- Module header comment
   that spans multiple lines -/
import Mathlib

namespace Demo

def s_p (p n : ℕ) : ℕ := (Nat.digits p n).sum

def carries (p D : ℕ) (d : Fin D → Fin p) : Fin D → ℕ
| i =>
  if h : i.val = 0 then 0 else 1
termination_by i => i.val

/- Lemma comment -/
theorem lemma_a (p m : ℕ) (hp : p ≥ 2) :
    p ^ 1 ≤ p ^ 2 := by
  have h_multiples_j_v_le : p ≥ 2 := by
    · exact hp
  suffices h_suf : p ≤ p * p by
    · grind
  set q := p ^ 2
  by_cases h_zero : m = 0
  · filter_upwards [Filter.eventually_ge_atTop 1] with x hx
    exact hx
  · have := Nat.le_refl p
    grind
    nlinarith

theorem theorem_main (n : ℕ) : n = n := by
  rfl

end Demo
"""
    doc = extract_infotree_heuristic(lean)
    assert doc.theorem_name == "theorem_main"

    # Zero comment/end/namespace leaks
    for node in doc.nodes:
        sl = node.source_slice.strip()
        assert not sl.startswith("-/")
        assert not sl.startswith("Module header")
        assert not sl.startswith("end ")
        assert not sl.startswith("namespace ")
        assert node.tactic_kind != "heuristic.·"

    # Both defs and both theorems are captured structurally
    kinds = [n.kind for n in doc.nodes]
    assert kinds.count("definition") == 2
    assert kinds.count("theorem") == 2

    # Check translated lines have valid safety and proper labels
    labels = []
    for idx, node in enumerate(doc.nodes, 1):
        pl = _translate_single_node_symbolic(node, idx, fidelity_mode=FidelityMode.LITERAL)
        assert validate_katex_safety(pl.latex) == []
        labels.append(pl.section_label)

    assert any("Definition (s_p)" in lbl for lbl in labels)
    assert any("Definition (carries)" in lbl for lbl in labels)
    assert any("Sufficient Condition" in lbl for lbl in labels)
    assert any("Case Split" in lbl for lbl in labels)
    assert any("Eventually / Filter Bound" in lbl for lbl in labels)
    assert any("Intermediate Fact" in lbl for lbl in labels)
    assert any("Automated Search" in lbl for lbl in labels)
    assert escape_latex_text("h_a") == r"h\_a"
