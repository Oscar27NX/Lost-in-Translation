# Purpose: Research and engineering ideas logged for future approval without unrequested implementation.

- **IDEA-001 (Mathlib-Linked InfoTree Extraction)**: Run `lean_extractor/InfoTreeDumper.lean` inside a Lean 4 / Mathlib Lake workspace on `erdos728.lean` and `Erdos728p.lean` so `symbolic_literal_v0_2` and small LMs receive true elaborated `goalsBefore` / `goalsAfter` states rather than heuristic approximations.
- **IDEA-002 (Declaration Picker + Lemma RAG)**: Split multi-theorem files (e.g., `Erdos728p.lean` with 259 lemmas + 130 defs) into a theorem-by-theorem navigator with dependency cross-referencing.
- **IDEA-003 (Frontend Proof Virtualization)**: Virtualize the step list and SVG provenance ribbon for 1,000+ step proofs.
- **IDEA-004 (Small LM QLoRA + Adversarial DPO Benchmark)**: Benchmark `Qwen2.5-Math-7B` and `Qwen2.5-14B` trained on HITL + adversarial DPO pairs against `symbolic_literal_v0_2` and prompted frontier models.
