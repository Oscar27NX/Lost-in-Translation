# Training Specialized Small LMs for Lost In Translation

## Why Fine-Tuned Small LMs (7B–32B) Instead of Prompting Giant Frontier Models?

Prompting a frontier model to *"translate this Lean 4 proof into a clean LaTeX proof"* fails systematically in formal verification workflows:

1. **Helpfulness Bias (Silent Gap Filling)**: Frontier chat models are optimized to sound coherent and helpful. If a Lean proof contains `sorry`, an unstated domain cast (`ℕ` truncated subtraction), or an opaque `linarith`/`omega` jump, frontier models routinely *fabricate* plausible-sounding prose that no longer matches the kernel proof term.
2. **Broken Provenance**: Without InfoTree state transitions (`goalsBefore` / `goalsAfter` + exact source spans), raw text translation loses line-level correspondence (`Lean L[x..y] → LaTeX ¶z`), making auditing long proofs (such as a future disproof of ETH) infeasible.
3. **Adversarial Contrast via Human-in-the-Loop (HITL) DPO**: Every time a mathematician flags or edits a line in the **Lost In Translation** workbench, the app records:
   - The exact Lean 4 InfoTree slice (`goalsBefore`, `goalsAfter`, `tacticKind`, `referencedConstants`)
   - The rejected LM output + structured error taxonomy (`semantic_drift`, `missing_hypothesis`, `quantifier_type_error`, `opaque_tactic_elision`, `notation_mismatch`, `hallucinated_step`)
   - The human-verified literal LaTeX (`chosen`)

## Quickstart

```bash
# 1. Build SFT + adversarial DPO JSONL from fixtures and any exported HITL reviews
python training/generate_adversarial_pairs.py \
  --hitl-jsonl path/to/exported_hitl.jsonl \
  --out-dir training/outputs

# 2. Validate QLoRA training config (CPU dry run)
python training/train_lora.py --config training/configs/qwen25_14b_qlora.yaml --stage sft --dry-run

# 3. Train Stage 1 (Literal SFT) and Stage 2 (Adversarial DPO) on GPU
python training/train_lora.py --config training/configs/qwen25_14b_qlora.yaml --stage sft
python training/train_lora.py --config training/configs/qwen25_14b_qlora.yaml --stage dpo

# 4. Serve the merged LoRA checkpoint via vLLM or Ollama and point Lost In Translation to http://localhost:8000/v1
```
