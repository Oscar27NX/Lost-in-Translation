# Purpose: Hypotheses linked to research questions and experimental checks.

## H1: Balanced-Argument Operator Recall in `symbolic_literal_v0_2` (Serves RQ1)

- **Claim**: Replacing flat token substitution (`symbolic_literal_v0_1`) with balanced-argument operator rewriting and an externalized Greek allowlist (`symbolic_literal_v0_2`) reduces plain-text `\mathrm{...}` / raw-symbol leaks across all 27 audited non-trivial operator classes in `data/raw/erdos728/erdos728.lean` to `0`, while maintaining `0` KaTeX parse errors and `0` KaTeX missing-metric warnings across `erdos728.lean`, `Erdos728p.lean`, and all 69 curated fixture expressions.
- **Status**: `proposed` (awaiting verification run and user confirmation).
- **Falsification / Failure Criterion**: Any remaining plain-text leak among the 27 operator classes in `erdos728.lean`, or any KaTeX parse error or missing-metric warning in `erdos728.lean` / `Erdos728p.lean`.
