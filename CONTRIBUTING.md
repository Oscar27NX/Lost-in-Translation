# Contributing to Lost In Translation

We welcome mathematicians, Lean 4 formalizers, ML researchers, and visualization designers!

## High-Impact Areas

1. **Curated Literal & Adversarial Pairs**: Submit verified Lean 4 `InfoTree` → LaTeX proofs (especially medium-to-long Mathlib proofs) along with adversarial negative annotations exported from the HITL workbench.
2. **Lean 4 `InfoTreeDumper` Enhancements**: Extend `lean_extractor/InfoTreeDumper.lean` to emit richer `TermInfo` subexpression spans, `calc` step trees, and Mathlib docstring cross-references.
3. **Small LM Fine-Tuning & Evaluation**: Benchmark 7B–32B open-weights checkpoints (`Qwen2.5-Math-7B`, `Qwen2.5-14B/32B`, `DeepSeek-Prover-V1.5`) on literal faithfulness, opaque-tactic detection, and `sorry` refusal.
4. **Long-Proof Visualization Scaling**: Improve hierarchical section folding, dependency-DAG overlays, and virtualized scrolling for 500+ line proofs (on the path toward formalizations like a disproof of ETH).

## Running Tests

```bash
# Backend tests
pytest backend/tests -v

# Training dataset builder smoke test
python training/generate_adversarial_pairs.py --out-dir training/outputs

# Frontend typecheck & production build
cd frontend && npm run build
```
