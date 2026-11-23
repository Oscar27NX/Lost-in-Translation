# Purpose: Directory and file map of the Lost In Translation repository.

## Top-Level Directories

- `backend/` — FastAPI server, Lean 4 `InfoTree` extractor, symbolic & LM translators, HITL storage, and pytest suite.
  - `backend/lit_core/` — Core application package (`api.py`, `extractor.py`, `translator.py`, `fixtures.py`, `schemas.py`, `storage.py`, `latex_fmt.py`, `latex_fmt_v2.py`).
  - `backend/lit_core/configs/` — Externalized translation config (`symbolic_operators.json`, `README.md`).
  - `backend/tests/` — Automated tests (`test_api.py`, `test_parser_and_latex.py`, `test_operator_recall.py`).
- `data/` — Datasets and runtime session storage (`data/sessions/` gitignored).
  - `data/raw/erdos728/` — Immutable raw benchmark Lean 4 files (`erdos728.lean`, `Erdos728p.lean`, `ORIGIN.md`, `README.md`).
- `docs/` — Project documentation, approved plans, decisions, hypotheses, ideas, and status logs.
  - `docs/plans/` — Implementation plans (`2026-11-23_symbolic-operator-recall.md`).
- `frontend/` — React + TypeScript + KaTeX HITL provenance workbench (`src/App.tsx`, `src/api.ts`, `src/types.ts`, `src/components/`).
- `lean_extractor/` — Native Lean 4 `InfoTreeDumper.lean`, `lakefile.toml`, `lean-toolchain`, and `examples/`.
- `scripts/` — Local development launchers (`dev.ps1`, `dev.sh`).
- `training/` — Adversarial DPO dataset builder (`generate_adversarial_pairs.py`, `schema.py`) and QLoRA SFT/DPO trainer (`train_lora.py`, `configs/`).

## Root Files

- `GEMINI.md` / `CLAUDE.md` — Scientific method, session lifecycle, and coding standards.
- `README.md` — Quickstart, architecture overview, and HITL-to-training workflow.
- `CONTRIBUTING.md` — Contributor guidelines.
- `LICENSE` — MIT License.
