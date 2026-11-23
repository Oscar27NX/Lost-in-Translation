# Purpose: Hand-checkable and full-file operator recall tests for symbolic_literal_v0_2 vs frozen v0_1.
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from lit_core.api import app
from lit_core.extractor import extract_infotree_heuristic
from lit_core.latex_fmt import lean_expr_to_latex, validate_katex_safety
from lit_core.latex_fmt_v2 import lean_expr_to_latex_v2
from lit_core.translator import _translate_single_node_symbolic

REPO_ROOT = Path(__file__).resolve().parents[2]
ERDOS_728_PATH = REPO_ROOT / "data" / "raw" / "erdos728" / "erdos728.lean"

# Operators that must NEVER degrade to plain-text \mathrm{...} in erdos728.lean under v0_2
BANNED_PLAIN_TEXT_OPERATORS = {
    "Tendsto",
    "atBot",
    "Filter.atBot",
    "Filter.map",
    "nhds",
    "choose",
    "fact",
    "descFactorial",
    "Nat.descFactorial",
    "factorization",
    "Nat.factorization",
    "floor",
    "ceil",
    "natAbs",
    "Int.natAbs",
    "Max.max",
    "Icc",
    "Ico",
    "Ioo",
    "Ioc",
    "range",
    "filter",
    "card",
    "sup",
    "Finset.sup",
    "biUnion",
    "Finset.biUnion",
    "image",
    "Finset.image",
    "Infinite",
    "Set.Infinite",
    "Nonempty",
    "Prime",
    "ZMOD",
    "eta",
    "theta",
    "mu",
    "kappa",
}


def test_operator_recall_hand_checkable_examples() -> None:
    cases = [
        ("Set (ℕ × ℕ × ℕ)", r"\times"),
        ("∀ᶠ ε : ℝ in 𝓝[>] 0, ε > 0", r"\mathcal{N}_{>}(0)"),
        ("Filter.Tendsto (fun M : ℕ => Real.log M) Filter.atTop Filter.atTop", r"\lim_{M \to +\infty}"),
        ("Filter.Tendsto f Filter.atTop (nhds 1)", r"\xrightarrow{+\infty} 1"),
        ("Filter.Tendsto (fun y => y) (Filter.map (fun x => 1 / x) Filter.atTop) (nhds 0)", r"(x \mapsto 1 / x)_{*}(+\infty)"),
        ("Filter.atBot", r"-\infty"),
        ("a + b > n + C * log n", r"\log n"),
        ("Nat.choose (2 * m) m", r"\binom{2 * m}{m}"),
        ("Nat.factorial a * Nat.factorial (a + b - n)", r"a! * (a + b - n)!"),
        ("Nat.descFactorial (m + k) k", r"(m + k)_{k}"),
        ("padicValNat p (Nat.choose (2 * m) m)", r"v_{p}(\binom{2 * m}{m})"),
        ("Nat.factorization (Nat.choose (m + k) k) p", r"v_{p}(\binom{m + k}{k})"),
        ("Nat.log p k", r"\lfloor \log_{p}(k) \rfloor"),
        ("Nat.floor ((2 * m) / p ^ k)", r"\lfloor (2 * m) / p^{k} \rfloor"),
        ("Nat.ceil (k / p)", r"\lceil k / p \rceil"),
        ("m ≡ -i [ZMOD p ^ k]", r"\pmod{p^{k}}"),
        ("Int.natAbs (i - i₀)", r"|i - i_{0}|"),
        ("Max.max M0 M1", r"\max(\mathrm{M0}, \mathrm{M1})"),
        ("Finset.Icc 1 k", r"[1, k]"),
        ("Finset.Ico 1 (j + 1)", r"[1, j + 1)"),
        ("Finset.range L", r"\{0, \dots, L - 1\}"),
        ("Finset.filter Nat.Prime (Finset.range n)", r"\{ p \in \{0, \dots, n - 1\} \mid p \text{ prime} \}"),
        ("((Finset.Icc 1 k).filter (fun i => p ^ j ∣ m + i)).card", r"|\{ i \in [1, k] \mid p^{j} \mid m + i \}|"),
        ("Finset.sup (Finset.Icc 1 k) (fun i => padicValNat p (m + i))", r"\sup_{i \in [1, k]} v_{p}(m + i)"),
        ("Finset.biUnion A (fun a => Finset.filter (fun m => m = a) S)", r"\bigcup_{a \in A}"),
        ("Finset.image (fun x => p * x) (Finset.Icc 1 k)", r"\{ p * x \mid x \in [1, k] \}"),
        ("S.Infinite ∧ A.Nonempty ∧ p.Prime", r"|S| = \infty \land A \neq \emptyset \land p \text{ prime}"),
        ("L * theta p + eta + mu + kappa", r"\theta"),
    ]
    for expr, expected_substr in cases:
        out = lean_expr_to_latex_v2(expr)
        assert validate_katex_safety(out) == [], f"Safety issue on {expr!r}: {out!r}"
        assert expected_substr in out, f"Expected {expected_substr!r} in {out!r} (from {expr!r})"


def test_invariants_greek_exclusion_and_frozen_baseline() -> None:
    # `omega` tactic must NOT become \omega; underscored `h_theta` must stay \mathrm{h\_theta}
    out = lean_expr_to_latex_v2("h_theta + theta + omega")
    assert r"\theta" in out
    assert r"\mathrm{h\_theta}" in out
    assert r"\mathrm{omega}" in out
    assert r"\omega" not in out

    # Frozen v0_1 baseline keeps original output untouched
    v1_out = lean_expr_to_latex("Filter.Tendsto (fun x => theta) Filter.atTop (nhds 0)")
    assert r"\mathrm{Tendsto}" in v1_out
    assert r"\mathrm{theta}" in v1_out


def test_erdos728_full_file_zero_operator_leaks() -> None:
    import re

    src = ERDOS_728_PATH.read_text(encoding="utf-8")
    doc = extract_infotree_heuristic(src, symbolic_variant="symbolic_literal_v0_2")
    assert len(doc.nodes) >= 350

    all_latex = [doc.statement_latex] + [
        _translate_single_node_symbolic(node, idx, symbolic_variant="symbolic_literal_v0_2").latex
        for idx, node in enumerate(doc.nodes, start=1)
    ]

    leaked: list[tuple[int, str, str]] = []
    for step_idx, tex in enumerate(all_latex):
        assert validate_katex_safety(tex) == [], f"Safety failure at index {step_idx}: {tex}"
        assert "𝓝" not in tex, f"Raw 𝓝 leaked at index {step_idx}: {tex}"
        assert r"\text{?}" not in tex, f"Unmapped non-ASCII leaked at index {step_idx}: {tex}"
        for m in re.finditer(r"\\mathrm\{([^{}]*)\}", tex):
            tok = m.group(1).replace(r"\_", "_")
            base_tail = tok.rsplit(".", 1)[-1]
            if tok in BANNED_PLAIN_TEXT_OPERATORS or (
                base_tail in ("card", "Infinite", "Nonempty", "Prime")
                and tok.rsplit(".", 1)[0] not in ("Finset", "Nat", "Set")
            ):
                leaked.append((step_idx, tok, tex[:160]))

    assert leaked == [], f"Plain-text operator leaks remaining: {leaked[:10]}"


def test_model_config_variant_selection_via_api() -> None:
    client = TestClient(app)
    orig_cfg = client.get("/api/config/model").json()
    lean_snippet = "lemma demo (p : ℕ) : Filter.Tendsto (fun x : ℝ => theta p) Filter.atTop (nhds 0) := by\n  sorry\n"
    try:
        # Select v0_1 explicitly
        cfg_v1 = {**orig_cfg, "backend_mode": "symbolic_baseline", "symbolic_variant": "symbolic_literal_v0_1"}
        assert client.put("/api/config/model", json=cfg_v1).status_code == 200
        r1 = client.post("/api/sessions", json={"title": "v1 check", "lean_source": lean_snippet})
        assert r1.status_code == 200
        assert r1.json()["model_id"] == "lit-symbolic-literal-v0.1"
        assert r"\mathrm{Tendsto}" in r1.json()["infotree"]["statement_latex"]

        # Select v0_2 explicitly
        cfg_v2 = {**orig_cfg, "backend_mode": "symbolic_baseline", "symbolic_variant": "symbolic_literal_v0_2"}
        assert client.put("/api/config/model", json=cfg_v2).status_code == 200
        r2 = client.post("/api/sessions", json={"title": "v2 check", "lean_source": lean_snippet})
        assert r2.status_code == 200
        assert r2.json()["model_id"] == "lit-symbolic-literal-v0.2"
        assert r"\lim_{x \to +\infty}" in r2.json()["infotree"]["statement_latex"]
        assert r"\theta" in r2.json()["infotree"]["statement_latex"]
    finally:
        client.put("/api/config/model", json=orig_cfg)
