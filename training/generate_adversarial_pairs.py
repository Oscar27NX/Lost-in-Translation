"""
Generate literal SFT and adversarial DPO preference pairs from:
  1. Built-in Lean 4 InfoTree fixtures (`backend/lit_core/fixtures.py`)
  2. Exported Human-in-the-Loop `.jsonl` files collected in the Lost In Translation UI

Usage:
  python training/generate_adversarial_pairs.py --out-dir training/outputs
  python training/generate_adversarial_pairs.py --hitl-jsonl data/exports/sqrt2_hitl.jsonl --out-dir training/outputs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "training"))

from lit_core.fixtures import build_lines_from_curated, get_curated_examples  # noqa: E402
from lit_core.schemas import FidelityMode, ProofLine  # noqa: E402
from lit_core.translator import ADVERSARIAL_LITERAL_SYSTEM_PROMPT, _build_node_user_prompt  # noqa: E402
from schema import DPOPreferenceExample, SFTExample  # noqa: E402


def _make_adversarial_negatives(line: ProofLine) -> list[tuple[str, str, str]]:
    """
    Synthesize realistic "helpful-but-unfaithful" model failures for DPO training.
    Returns list of (perturbation_type, rejected_latex, flaw_description).
    """
    negatives: list[tuple[str, str, str]] = []
    ltx = line.latex

    # 1. Domain / coercion error (e.g. conflating |a| ∈ ℕ with a ∈ ℕ or dropping positivity)
    if r"|a|" in ltx:
        negatives.append(
            (
                "domain_coercion_error",
                ltx.replace(r"|a|", "a"),
                "Silently dropped absolute value / ℤ→ℕ coercion `q.num.natAbs`.",
            )
        )

    # 2. Dropped hypothesis / precondition (e.g. dropping 0 ≤ 2 or b > 0 or 0 < k)
    if r"0 \le 2" in ltx or r"0 < k" in ltx or r"b > 0" in ltx:
        dropped = re.sub(r"\\text\{ and \} 0 \\le 2", "", ltx)
        dropped = dropped.replace(r"0 < k \le 2^{n+1}", r"k \le 2^{n+1}")
        dropped = dropped.replace(r"b > 0", r"b \neq 1")
        if dropped != ltx:
            negatives.append(
                (
                    "dropped_hypothesis",
                    dropped,
                    "Dropped required positivity/nonnegativity guard from Lean proof state.",
                )
            )

    # 3. Quantifier / order flip
    if r"\le" in ltx:
        negatives.append(
            (
                "quantifier_flip",
                ltx.replace(r"\le", "<", 1),
                "Unfaithfully strengthened non-strict inequality ≤ to strict <.",
            )
        )
    elif r"\forall" in ltx:
        negatives.append(
            (
                "quantifier_flip",
                ltx.replace(r"\forall", r"\exists", 1),
                "Flipped universal quantifier ∀ to existential ∃.",
            )
        )

    # 4. Hidden opaque automation leap (pretending `linarith`/`omega` was a trivial identity)
    if line.derivation.opaque_automation:
        negatives.append(
            (
                "hidden_opaque_leap",
                r"\text{By direct simplification, the required identity holds immediately.}",
                "Hand-waved an opaque automation tactic (`linarith`/`omega`/`simp`) without showing the derived mathematical relation.",
            )
        )

    return negatives


def build_datasets(hitl_paths: list[Path], out_dir: Path) -> tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    sft_rows: list[dict] = []
    dpo_rows: list[dict] = []

    # Part 1: Curated verified InfoTree examples + synthetic adversarial negatives
    for key, ex in get_curated_examples().items():
        node_map = {n.node_id: n for n in ex.infotree.nodes}
        lines = build_lines_from_curated(ex, fidelity_mode=FidelityMode.LITERAL)
        for line in lines:
            node = node_map[line.infotree_node_ids[0]]
            user_prompt = _build_node_user_prompt(
                node=node,
                theorem_statement=ex.infotree.statement_lean,
                fidelity_mode=FidelityMode.LITERAL,
            )
            assistant_json = json.dumps(
                {
                    "latex": line.latex,
                    "section_label": line.section_label,
                    "procedure": line.derivation.procedure,
                    "justification": line.derivation.justification,
                    "confidence": line.derivation.confidence,
                    "opaque_automation": line.derivation.opaque_automation,
                    "warnings": [c.detail for c in line.derivation.checks if c.status != "pass"],
                },
                ensure_ascii=False,
            )
            sft_rows.append(
                SFTExample(
                    messages=[
                        {"role": "system", "content": ADVERSARIAL_LITERAL_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                        {"role": "assistant", "content": assistant_json},
                    ],
                    metadata={"source": "curated_fixture", "example": key, "line_id": line.line_id},
                ).to_dict()
            )

            for pert_type, bad_latex, flaw in _make_adversarial_negatives(line):
                bad_json = json.dumps(
                    {
                        "latex": bad_latex,
                        "section_label": line.section_label,
                        "procedure": ["Fluent paraphrase omitting formal verification checks."],
                        "justification": "Plausible-sounding but unfaithful translation.",
                        "confidence": 0.99,
                        "opaque_automation": False,
                        "warnings": [],
                    },
                    ensure_ascii=False,
                )
                dpo_rows.append(
                    DPOPreferenceExample(
                        prompt=user_prompt,
                        chosen=assistant_json,
                        rejected=bad_json,
                        perturbation_type=pert_type,  # type: ignore[arg-type]
                        metadata={"source": "synthetic_adversarial", "example": key, "line_id": line.line_id, "flaw": flaw},
                    ).to_dict()
                )

    # Part 2: Ingest real Human-in-the-Loop exports from the UI
    for hp in hitl_paths:
        if not hp.exists():
            continue
        for raw_line in hp.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            rec = json.loads(raw_line)
            rtype = rec.get("record_type")
            prompt_str = json.dumps(rec.get("input", {}), ensure_ascii=False, indent=2)
            if rtype == "sft":
                sft_rows.append(
                    SFTExample(
                        messages=[
                            {"role": "system", "content": ADVERSARIAL_LITERAL_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt_str},
                            {"role": "assistant", "content": json.dumps(rec["output"], ensure_ascii=False)},
                        ],
                        metadata={"source": "hitl_verified", "session_id": rec.get("session_id"), "line_id": rec.get("line_id")},
                    ).to_dict()
                )
            elif rtype == "dpo_preference":
                dpo_rows.append(
                    DPOPreferenceExample(
                        prompt=prompt_str,
                        chosen=rec["chosen"],
                        rejected=rec["rejected"],
                        perturbation_type="human_hitl_correction",
                        metadata={
                            "source": "hitl_correction",
                            "flag_categories": rec.get("flag_categories", []),
                            "reviewer_notes": rec.get("reviewer_notes", []),
                        },
                    ).to_dict()
                )

    sft_path = out_dir / "sft_literal_train.jsonl"
    dpo_path = out_dir / "dpo_adversarial_train.jsonl"
    sft_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in sft_rows) + "\n", encoding="utf-8")
    dpo_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in dpo_rows) + "\n", encoding="utf-8")
    return len(sft_rows), len(dpo_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SFT + Adversarial DPO datasets for Lost In Translation.")
    parser.add_argument("--hitl-jsonl", nargs="*", default=[], help="Optional exported HITL JSONL files from the UI.")
    parser.add_argument("--out-dir", default="training/outputs", help="Output directory for JSONL datasets.")
    args = parser.parse_args()

    n_sft, n_dpo = build_datasets([Path(p) for p in args.hitl_jsonl], Path(args.out_dir))
    print(f"[LIT Dataset Builder] Wrote {n_sft} SFT examples and {n_dpo} adversarial DPO pairs to {args.out_dir}")


if __name__ == "__main__":
    main()
