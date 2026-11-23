# Purpose: Current repository status, verification results, reviewed items, and next steps.

## Current State (2026-11-23)

- **Active Plan**: `docs/plans/2026-11-23_symbolic-operator-recall.md` (`approved`, all 6 steps executed).
- **Default Symbolic Variant**: `symbolic_literal_v0_2` (`backend/lit_core/latex_fmt_v2.py`), parameterized by `backend/lit_core/configs/symbolic_operators.json`; frozen `symbolic_literal_v0_1` (`backend/lit_core/latex_fmt.py`) remains selectable via `ModelConfig`.
- **Live Server**: `uvicorn lit_core.api:app --host 127.0.0.1 --port 8000`.

## Latest Verification Results (2026-11-23)

- `ruff check --config backend/pyproject.toml backend training`: passed (`0` errors).
- `pytest backend/tests -v`: `12 passed` (`test_api.py`, `test_parser_and_latex.py`, `test_operator_recall.py`).
- Head-to-head Node KaTeX validation (`throwOnError: true`):
  - `curated` fixtures: `69 / 69` OK, `0` parse errors, `0` metric warnings.
  - `erdos728.lean` (`symbolic_literal_v0_1`): `399 / 399` OK, `0` parse errors, `2` metric warnings (`𝓝`).
  - `erdos728.lean` (`symbolic_literal_v0_2`): `399 / 399` OK, `0` parse errors, `0` metric warnings, `0` plain-text operator leaks across all 27 operator classes.
  - `Erdos728p.lean` (`symbolic_literal_v0_1`): `1817 / 1817` OK, `0` parse errors, `0` metric warnings.
  - `Erdos728p.lean` (`symbolic_literal_v0_2`): `1817 / 1817` OK, `0` parse errors, `0` metric warnings.
- `frontend` (`tsc -b && vite build`): passed (`0` errors).

## Unreviewed Items (Pending User Confirmation)

- `docs/PROJECT.md` (drafted from `README.md`, `LICENSE`, and `backend/pyproject.toml`).
- `docs/HYPOTHESES.md` (`H1` status proposed for transition to `supported` after user review of `erdos728.lean` results).
- `data/raw/erdos728/ORIGIN.md` (upstream source URL, Mathlib version, and upstream license for `erdos728.lean` and `Erdos728p.lean`).
- Visual inspection of `symbolic_literal_v0_2` output and variant selector in the web UI (`http://127.0.0.1:8000`).

## Exact Next Step

1. Review `symbolic_literal_v0_2` output on `erdos728.lean` in the UI (`http://127.0.0.1:8000`) and confirm `H1` status, `docs/PROJECT.md` fields, and `data/raw/erdos728/ORIGIN.md` upstream license metadata.
