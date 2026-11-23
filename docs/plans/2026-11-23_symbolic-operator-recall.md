# Purpose: Approved implementation plan for expanding symbolic operator recall (`symbolic_literal_v0_2`).

- **Status**: `approved (2026-11-23)`
- **Serves**: `RQ1` (Symbolic Recall & Faithfulness Ceiling)
- **Approved Decisions**:
  - `D1` = Option B: Freeze `backend/lit_core/latex_fmt.py` as `symbolic_literal_v0_1`; implement the balanced-argument operator translator in `backend/lit_core/latex_fmt_v2.py` (`symbolic_literal_v0_2`), selectable via `ModelConfig.symbolic_variant`.
  - `D2` = Option A: Balanced-argument structured rewriting for all 27 non-trivial Lean/Mathlib operator classes audited in `data/raw/erdos728/erdos728.lean`.
  - `D3` = Option A: Externalized ASCII Greek variable allowlist (`alpha`..`psi`, excluding `omega`) in `backend/lit_core/configs/symbolic_operators.json`.
  - `R1` + `R2`: Initialize `docs/` research logs, archive `erdos728.lean` & `Erdos728p.lean` in `data/raw/erdos728/`, and add `backend/tests/test_operator_recall.py`.

## Steps

1. Archive `erdos728.lean` and `Erdos728p.lean` under `data/raw/erdos728/` with `ORIGIN.md` and `README.md`.
2. Initialize `docs/` governance logs (`PROJECT.md`, `METHOD.md`, `DECISIONS.md`, `HYPOTHESES.md`, `IDEAS.md`, `STATUS.md`, `MAP.md`).
3. Externalize operator, Unicode, and Greek allowlist tables into `backend/lit_core/configs/symbolic_operators.json`.
4. Implement `backend/lit_core/latex_fmt_v2.py` leaving `backend/lit_core/latex_fmt.py` untouched.
5. Wire `symbolic_variant` through `ModelConfig` (`schemas.py`), `extractor.py`, `translator.py`, `api.py`, and frontend config UI (`types.ts`, `Modals.tsx`, `App.tsx`).
6. Verify with `ruff`, `pytest` (including `test_operator_recall.py`), head-to-head Node KaTeX + operator leak checks (`v0_1` vs `v0_2`) on `erdos728.lean`, `Erdos728p.lean`, and curated fixtures, plus `npm run build`.
