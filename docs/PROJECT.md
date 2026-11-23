# Purpose: Canonical project definition, research questions, scope, and terminology for Lost In Translation.

## Project Identity

- **Title**: Lost In Translation (`lost-in-translation`)
- **Initial Release Version**: `v0.1.0` (2026-11-20, initial commit `adfc1c2`)
- **License**: MIT License (`LICENSE` in repository root)
- **Languages & Stack**: Python 3.11+ (FastAPI, Pydantic, PyTorch/PEFT/TRL training), TypeScript / React + KaTeX (`frontend/`), Lean 4 (`lean_extractor/`).
- **Target Venue / Goal**: Open-source software release and reproducible research workbench for faithful formal-to-informal proof translation.
- **Note on Provenance**: Drafted from `README.md`, `LICENSE`, `backend/pyproject.toml`, and session records on 2026-11-23; awaiting user confirmation in `STATUS.md`.

## Problem Statement

Prompting generic frontier LLMs to translate Lean 4 proofs into LaTeX suffers from helpfulness bias: models silently fill gaps (including `sorry`), drop domain/positivity preconditions (`ℕ` truncated subtraction, `ℤ → ℝ` coercions), and hand-wave opaque tactics (`linarith`, `omega`, `simp`, `aesop`). Auditing long formal proofs requires exact line-level provenance (`LaTeX Step z ← Lean L[x..y]`), explicit exposure of opaque automation, and Human-in-the-Loop (HITL) flagging and correction.

## Goals & Scope

- Extract Lean 4 `InfoTree` state transitions (`goalsBefore` → `goalsAfter`, spans, referenced constants) natively when Lean 4 is available, with a deterministic heuristic parser fallback.
- Support both zero-GPU deterministic symbolic literal translation baselines and local specialized open-weights small LMs (7B–32B via Ollama / vLLM / llama.cpp).
- Provide an interactive HITL data visualization workbench for line verification, structured flagging, inline KaTeX editing, and targeted single-line regeneration.
- Close the flywheel by exporting verified/edited/flagged lines into SFT and adversarial DPO datasets (`training/`).

## Research Questions

- **RQ1 (Symbolic Recall & Faithfulness Ceiling)**: How far can deterministic `InfoTree`/symbolic literal translation rules reach in operator recall and KaTeX well-formedness on real Mathlib formalizations (such as `erdos728.lean` and `Erdos728p.lean`), and where is the semantic ceiling requiring kernel `InfoTree` goal states and ML?
- **RQ2 (Specialized Small LM Faithfulness)**: Do fine-tuned 7B–32B open-weights models trained via literal SFT and adversarial HITL DPO outperform prompted frontier models on faithfulness metrics (eliminating silent gap filling, dropped hypotheses, and `sorry` masking)?
- **RQ3 (HITL Provenance Auditing)**: How effectively do synchronized Lean-to-LaTeX provenance ribbons, step-level metadata inspection, and single-line targeted regeneration enable mathematicians to audit and repair long proofs?

## Terminology

- **InfoTree**: Lean 4 elaborator data structure recording tactic syntax spans, local contexts, `goalsBefore` / `goalsAfter` metavariable states, and referenced constants.
- **Symbolic-Literal Baseline (`symbolic_literal_v0_1`, `symbolic_literal_v0_2`)**: Deterministic zero-GPU rule-based translator mapping InfoTree nodes to KaTeX-validated LaTeX.
- **Opaque Automation**: Automated Lean tactics (`linarith`, `nlinarith`, `omega`, `simp`, `aesop`, `grind`, `field_simp`, `norm_num`, etc.) whose internal proof trace is compressed into one tactic invocation.
- **HITL Flywheel**: Capturing human verification, structured error flags, and edits in the UI as SFT and DPO preference pairs.
