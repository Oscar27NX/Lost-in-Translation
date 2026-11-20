from __future__ import annotations

from fastapi.testclient import TestClient
from lit_core.api import app
from lit_core.extractor import extract_infotree_heuristic
from lit_core.schemas import FlagCategory, LineStatus

client = TestClient(app)


def test_health_and_examples() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"

    ex = client.get("/api/examples")
    assert ex.status_code == 200
    keys = {e["key"] for e in ex.json()}
    assert "irrational_sqrt_two" in keys
    assert "harmonic_series_diverges" in keys
    assert "exists_infinite_primes" in keys


def test_session_hitl_lifecycle_and_exports() -> None:
    # Create curated √2 session
    r = client.post("/api/sessions", json={"example_key": "irrational_sqrt_two", "fidelity_mode": "literal"})
    assert r.status_code == 200
    sess = r.json()
    sid = sess["session_id"]
    assert len(sess["lines"]) == 8
    assert sess["metrics"]["opaque_tactic_count"] >= 2

    # Flag line 4 (opaque field_simp/linarith step)
    target_line = sess["lines"][3]
    r_flag = client.patch(
        f"/api/sessions/{sid}/lines/{target_line['line_id']}",
        json={
            "flag_categories": [FlagCategory.OPAQUE_TACTIC_ELISION.value],
            "flag_comment": "Please unpack field_simp and zify cast explicitly.",
        },
    )
    assert r_flag.status_code == 200
    flagged = r_flag.json()["lines"][3]
    assert flagged["status"] == LineStatus.FLAGGED.value
    assert len(flagged["flags"]) == 1

    # Targeted regeneration of just line 4 in expanded mode
    r_regen = client.post(
        f"/api/sessions/{sid}/lines/{target_line['line_id']}/regenerate",
        json={"fidelity_mode": "expanded", "use_active_flags": True, "instruction": "Keep explicit cast injectivity."},
    )
    assert r_regen.status_code == 200
    regenerated = r_regen.json()["lines"][3]
    assert len(regenerated["revisions"]) == 2
    assert "injectivity" in regenerated["latex"]

    # Human edit + verify line 1
    line1 = sess["lines"][0]
    custom_latex = r"\text{Suppose for contradiction that } \sqrt{2} = q \in \mathbb{Q}."
    r_edit = client.patch(
        f"/api/sessions/{sid}/lines/{line1['line_id']}",
        json={"latex": custom_latex, "status": LineStatus.EDITED.value},
    )
    assert r_edit.status_code == 200
    assert r_edit.json()["lines"][0]["latex"] == custom_latex

    # Revert revision on line 4 back to v0
    r_rev = client.post(f"/api/sessions/{sid}/lines/{target_line['line_id']}/revert/0")
    assert r_rev.status_code == 200
    assert r_rev.json()["lines"][3]["latex"] == target_line["latex"]

    # Export LaTeX with provenance
    r_tex = client.get(f"/api/sessions/{sid}/export/latex?provenance=true")
    assert r_tex.status_code == 200
    assert r"\begin{theorem}" in r_tex.text
    assert "LIT Step 1" in r_tex.text

    # Export HITL SFT + DPO JSONL
    r_ds = client.get(f"/api/sessions/{sid}/export/dataset")
    assert r_ds.status_code == 200
    assert '"record_type": "dpo_preference"' in r_ds.text
    assert '"record_type": "sft"' in r_ds.text


def test_custom_lean_heuristic_extraction_and_sorry_detection() -> None:
    custom_lean = """
theorem add_zero_demo (n : ℕ) : n + 0 = n := by
  have h1 : n + 0 = n := by
    sorry
  exact h1
"""
    doc = extract_infotree_heuristic(custom_lean)
    assert doc.theorem_name == "add_zero_demo"
    assert doc.extractor_mode == "heuristic_parser"
    assert len(doc.nodes) >= 2

    r = client.post("/api/sessions", json={"title": "Demo sorry check", "lean_source": custom_lean})
    assert r.status_code == 200
    lines = r.json()["lines"]
    assert any("UNPROVED GAP" in pl["latex"] for pl in lines)


def test_all_curated_examples_span_bounds_and_modes() -> None:
    for key in ("irrational_sqrt_two", "harmonic_series_diverges", "exists_infinite_primes"):
        for mode in ("literal", "expanded", "formal_prose"):
            r = client.post("/api/sessions", json={"example_key": key, "fidelity_mode": mode})
            assert r.status_code == 200
            sess = r.json()
            total_src_lines = len(sess["infotree"]["source_code"].splitlines())
            assert len(sess["lines"]) >= 5
            for pl in sess["lines"]:
                sp = pl["lean_span"]
                assert 1 <= sp["start_line"] <= sp["end_line"] <= total_src_lines
                assert pl["latex"].strip() != ""
                assert pl["derivation"]["justification"].strip() != ""
                assert len(pl["derivation"]["procedure"]) >= 1

