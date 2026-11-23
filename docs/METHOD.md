# Purpose: Method specification, registered translation variants, notation, and configuration parameters.

## Pipeline Architecture

1. **Extraction (`backend/lit_core/extractor.py`)**:
   - Curated fixtures: matched verbatim and loaded from `backend/lit_core/fixtures.py`.
   - Native Lean 4 InfoTree: `lean_extractor/InfoTreeDumper.lean` via `lake exe infotree_dumper` when `lean` and `lake` are on `PATH`.
   - Heuristic Fallback: `extract_infotree_heuristic` strips nested block/line comments while preserving line numbers, separates top-level `def`/`theorem` declarations from tactic bodies, tracks delimiters and `·` bullets, and extracts tactic spans.
2. **Translation (`backend/lit_core/translator.py`)**:
   - Selects between `symbolic_baseline` (deterministic) and `openai_compatible_lm` (local 7B–32B LM via Ollama/vLLM/llama.cpp).
   - Runs structural KaTeX validation (`validate_katex_safety`) before returning `ProofLine` outputs.
3. **HITL Review & Dataset Export (`backend/lit_core/storage.py`)**:
   - Captures `verified`, `flagged` (6-category taxonomy), `edited`, and `regenerated` revisions into SFT and DPO `.jsonl` training records.

## Registered Translation Variants

| Variant ID (`ModelConfig`) | Module | Effective `model_id` | Description |
| --- | --- | --- | --- |
| `symbolic_literal_v0_1` | `backend/lit_core/latex_fmt.py` | `lit-symbolic-literal-v0.1` | **Frozen baseline.** Single-pass token formatter with KaTeX brace/subscript/modulo escaping and minimal identifier map. |
| `symbolic_literal_v0_2` (default) | `backend/lit_core/latex_fmt_v2.py` | `lit-symbolic-literal-v0.2` | **Balanced-argument operator variant.** Rewrites 27 Lean/Mathlib operator classes, dot-method suffixes, `Filter.Tendsto` limits, punctured neighborhoods `𝓝[>]`, and externalized ASCII Greek identifiers. |
| `openai_compatible_lm` | `backend/lit_core/translator.py` | Configured `model_name` | Queries an OpenAI-compatible 7B–32B checkpoint with strict JSON schema and InfoTree goal states. |

## Externalized Parameters (`backend/lit_core/configs/symbolic_operators.json`)

- `text_unicode_map`: Unicode-to-ASCII transliterations for KaTeX `\text{...}` and `\texttt{...}` modes.
- `math_unicode_map`: Unicode-to-KaTeX math symbol mappings (including `×` and `𝓝`).
- `subscript_digit_map`: Trailing Unicode subscripts (`₀`..`₉`, `₊`, `₋`, `ᵥ`, `ᶠ`).
- `greek_ascii_allowlist`: Exact ASCII Greek variable names mapped to LaTeX symbols (`omega` excluded to avoid collision with the `omega` tactic).
- `simple_ident_map`: Direct token replacements (`Filter.atTop`, `Filter.atBot`, `Real.log`, `log`, `Real.exp`, `exp`, `Real.sqrt`, `Nat.gcd`, `nhds`, Lean keywords).
- `max_input_len`, `max_output_len`, `max_code_len`: Input/output truncation bounds.
