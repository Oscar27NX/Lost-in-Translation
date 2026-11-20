# Lost In Translation

**From a Lean 4 `InfoTree` source to a LaTeX Proof Workbench with Human-in-the-Loop Provenance Auditing.**

> *Instead of prompting a giant frontier model to be "helpful" and smooth over gaps, **Lost In Translation** extracts formal Lean 4 `InfoTree` state transitions (`goalsBefore` → `goalsAfter`, exact source spans, and referenced constants), feeds them to specialized open-weights small LMs, and places Human-in-the-Loop line features such as flagging, editing, and targeted regeneration at the center of the workflow.*

---

## Why "Lost In Translation"?

Translating formalized proofs (Lean 4) back into readable formal text without distorting semantical truth is a non-trivial problem which is becoming more and more relevant as LLMs begin to be used as automated proof solvers:

- **Frontier chat models hallucinate**: frontier models frequently drop positivity/coercion preconditions (`ℕ` truncated subtraction, `|a| = q.num.natAbs`), gloss over opaque automation tactics (`linarith`, `omega`, `simp`, `field_simp`), or invent plausible-sounding bridges across `sorry`.
- **Scaling to massive proofs requires provenance**: Auditing long formal proofs can become more accessible with **line-by-line provenance**, live goal-state inspection, and single-line regeneration.
- **Every human review improves the specialized model**: Flagging defects with a formal error taxonomy (`semantic_drift`, `missing_hypothesis`, `quantifier_type_error`, `opaque_tactic_elision`, `notation_mismatch`, `hallucinated_step`) and editing LaTeX directly exports **SFT + Adversarial DPO JSONL** datasets for QLoRA fine-tuning of 7B–32B models (`Qwen2.5-Math-7B`, `Qwen2.5-14B/32B`, `DeepSeek-Prover-V1.5`).

---

## Architecture

This is an initial prototype implemented with Gemini Neon. It receives a Lean source file, parses it using the Lean 4 InfoTree dumper, and then translates it into LaTeX using a specialized LM. It also provides an interface for reviewing and editing the generated LaTeX.

## Included Proofs (Demo)
1. **Irrationality of $\sqrt{2}$** (`irrational_sqrt_two`) — Full coprime integer descent with explicit $\mathbb{R} \to \mathbb{Z} \to \mathbb{N}$ coercion tracking (`q.num.natAbs`) and highlighted opaque tactics (`field_simp`, `linarith`, `norm_num`).
2. **Divergence of the Harmonic Series** (`harmonic_series_diverges`) — Oresme's dyadic block-grouping induction $H_{2^n} \ge 1 + n/2$, `calc` chain alignment, and `omega` / `linarith` audit diagnostics.
3. **Infinitude of Primes** (`exists_infinite_primes`) — Euclid's factorial construction $n! + 1$ with contradiction subproof indentation.
4. **Custom Lean 4 Editor** — Paste or modify any Lean 4 proof (try inserting a `sorry` to see literal unproved-gap detection).

---

## Getting started

### Prerequisites
- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) (or `pip`)
- Node.js 20+ and `npm`
- *(Optional)* Lean 4 + `lake` (`elan`) for live kernel `InfoTree` extraction
- *(Optional)* Ollama / vLLM / llama.cpp serving any local 7B–32B open-weights model

### Start the Backend (FastAPI)

```powershell
# Using uv (recommended)
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -e "backend[dev]"
.venv/Scripts/uvicorn.exe lit_core.api:app --reload --port 8000
```

*(On Linux/macOS replace `.venv/Scripts/...` with `.venv/bin/...`.)*

### Start the Frontend (React + Vite + KaTeX)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

Or use the helper scripts:
- Windows PowerShell: `.\scripts\dev.ps1`
- macOS / Linux: `./scripts/dev.sh`

---

## Connecting a Local Fine-Tuned Small LM (7B–32B)

Click the **Symbolic-Literal Baseline** pill in the top header to open **Model Configuration**:

1. Select **Local Specialized Small LM (7B–32B)**.
2. Point to your local OpenAI-compatible endpoint:
   - **Ollama**: `http://localhost:11434/v1` (e.g., `qwen2.5-math:7b-instruct` or `qwen2.5:14b-instruct`)
   - **vLLM**: `http://localhost:8000/v1` (e.g., your merged LoRA checkpoint `lit-qwen25-14b-lean2latex`)
3. Click **Test Connection** and **Save Configuration**.

---

## Live Lean 4 `InfoTreeDumper`

If you have `elan` / Lean 4 installed, build the native extractor:

```bash
cd lean_extractor
lake build infotree_dumper
lake exe infotree_dumper examples/IrrationalSqrt2.lean
```

When `lake` and `lean` are on `PATH`, the backend automatically invokes `infotree_dumper` for custom Lean 4 proofs and displays **Live Lean 4 InfoTree** in the source pane header.

---

## Keyboard Shortcuts (Audit Mode)

| Key | Action |
| --- | --- |
| `j` / `↓` | Select next proof step |
| `k` / `↑` | Select previous proof step |
| `v` | Toggle Verified status on selected step |
| `f` | Flag faithfulness defect on selected step |
| `e` | Open inline LaTeX editor with live KaTeX preview |
| `r` | Open targeted single-line regeneration controls |
| `Esc` | Close active inline editor / popover / modal |

---

## Repository Layout

```text
Lost-in-Translation/
├── lean_extractor/          # Native Lean 4 InfoTree metaprogramming dumper + example .lean proofs
├── backend/                 # FastAPI service, InfoTree extractor, pluggable LM translator, HITL storage
│   ├── lit_core/
│   └── tests/
├── frontend/                # React + TypeScript + KaTeX bipartite provenance workbench
├── training/                # Adversarial DPO pair generator + QLoRA SFT/DPO trainer (7B–32B)
└── scripts/                 # Local dev launchers (dev.ps1 / dev.sh)
```

## License

See [LICENSE](LICENSE).
