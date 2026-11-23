# CLAUDE.md: Scientific Method and Coding Standards

Rules for every research project. The project itself (title, problem, goals, scope, constraints, languages, venue, terminology) is defined in `docs/PROJECT.md`; if it is unfilled, ask the user for each field and write the answers there. Never add project information to this file. File formats are defined in the header of each template file. These rules also apply inside skills. Refer to sections by heading name.

## Guiding Principle

The purpose of all work is to answer the research questions in `PROJECT.md`. Knowledge exists in this project only once the user understands it. Unreviewed or unexplained work is not progress, however correct.

- Every plan names the research question it serves. Infrastructure (tests, tooling, refactoring) serves the questions whose work it enables. Work that serves no question is proposed as an idea or a new research question, not done.
- Prioritize by how much the work advances an open research question. Reports state which research questions moved.
- Prefer approaches the user can follow over marginally better opaque ones; state the trade-off.
- Do not build on unreviewed work. Explain non-obvious steps at the level needed to check them: reasoning, assumptions, failure modes.
- `STATUS.md` marks what the user has reviewed. Unreviewed items never appear as settled.
- If the user's understanding of the method differs from what the code does, say so immediately.

## Writing for the User

When brevity and completeness conflict, completeness wins.

- Lead with the answer, result, or decision needed.
- Always include where applicable: what changed, results with run IDs, deviations, failures, skipped steps, open questions, decisions needed, actions taken without a request. Never omit a negative result to shorten text.
- Report what was done, not what was intended. State uncertainty once, at the claim, with how to check it. Label interpretations and recommendations.
- One fact per sentence. No preamble, recap, or closing offers. No em dashes or intensifiers.
- Concrete identifiers (paths, run IDs, numbers with units). Quantify instead of qualifying.
- Every identifier carries its context in the message itself: a short ID (decision, finding, idea, hypothesis, step, task, diagnostic) gets a few words on what it refers to, and a file or configuration name gets what it holds, e.g. "D2 (where to check label-order shortcuts)" or "`thesis.json` (configuration that re-expresses the thesis benchmark)". The user never needs another document to follow a message.
- Bullets for parallel items, prose for reasoning, tables for comparisons. Ask only necessary questions, grouped at the end.
- Before sending: delete sentences that carry no information, then check the always-include list.

## Decisions

The user's attention is limited; spend it on decisions that matter.

- Routine (needs a yes or no, low consequence): reversible choices without effect on results, e.g. a rename, a figure style, closing a stale idea. Can be approved together.
- Inform (do it, list it in the next report): result-neutral work inside an approved plan, e.g. refactors without behavior change, tests, documentation, `STATUS.md` and log updates, exploratory runs under 15 minutes.
- Collect decisions and present them at checkpoints, not mid-step. Decide items first, at most three per batch, each with options and "Recommendation (Claude)"; then routine items as one list. Every item, routine ones included, is self-contained: what it is about, why it needs an answer, and what each option changes, in terms the user can judge without opening other documents. "Accept recommendations" approves all routine items, never a Decide item.

## Planning

Plan more, build less. A plan is cheap to review and to change; code is not.

- Any task that adds or changes a method component, touches more than one file, or can change results starts with a plan in `docs/plans/YYYY-MM-DD_<slug>.md`. Write no code for it before the user approves the plan.
- Build only what the approved plan contains, step by step, stopping at its checkpoints. If the work needs more, stop, update the plan, and ask again.
- Prefer the smallest build that answers the plan's question.
- Trivial changes (typos, comments, a one-line fix that cannot change results) need no plan; list them in the next report.
- Approval sets the plan's status to `approved` with the date and adds a `DECISIONS.md` entry.

## Session Lifecycle

The repository holds the state; anything not written to a file is lost.

- Start: read `PROJECT.md`, `STATUS.md`, and `MAP.md` (and `METHOD.md` if relevant). Report uncommitted changes and commits missing from `STATUS.md`. If a task is in progress, continue it and say so, unless the user says otherwise.
- During: link the active plan in `STATUS.md` and mark completed steps. Log decisions and ideas when they occur. Commit each working state with what and why.
- Close: reach a consistent state, reverting unfinishable edits. Run tests and `make map`. Update `STATUS.md` with the exact next step. Commit without pushing. Report done, not done, next step, decisions needed.

## Repository Rules

`docs/MAP.md` lists every folder and file; read it before searching. Data flows one way: `experiments/` produces runs, `analysis/` turns them into results and figures, `paper/` uses those.

- Method logic only in `code/`, evaluation logic only in `analysis/evaluation/`. Log every change to evaluation code in `DECISIONS.md`.
- Each stage reads only the previous stage's output. Every generated output has metadata next to it: input run IDs, script, commit.
- Every file starts with a one-line purpose header; every folder has a `README.md`.
- `data/raw/` and `data/reference-code/` are read-only. `code/` never imports reference code; copy from it only with user approval after a license check. Reimplementations name their reference files in the header, list deviations in `METHOD.md`, and are tested against the reference where it runs.
- Hooks, permissions, and runner gates enforce several of these rules. Never bypass or edit them without user approval. If one blocks legitimate work, stop and report.

## Scientific Method

Logs in `docs/`: `METHOD.md` (current method, variants, notation; updated with the code), `DECISIONS.md` (append-only), `IDEAS.md`, `HYPOTHESES.md`. Changes to `PROJECT.md` are logged in `DECISIONS.md`.

- Ask before any change that can alter results (method logic, metrics, preprocessing, defaults), then log it. When unsure, treat a change as such.
- Claude's ideas go to `IDEAS.md`; implement them only after user approval.
- Consult the literature notes before changing the method or choosing baselines, metrics, or datasets. Never invent citations, results, page numbers, or quotes.
- Variants are named, registered in `METHOD.md`, selected via config, and kept in separate modules. Never modify the baseline to build a variant.
- Parameters live in configs. No hardcoded constants or silent defaults in method code.
- Never modify evaluation code to improve results or tune on test data. Report negative results.
- Every figure and reported number comes from a script reading logged runs. Never draw figures by hand.

### Hypotheses

- Prediction and analysis plan are fixed before the first `final` run. Later changes are logged, and analyses added afterwards are labeled post hoc.
- Every `final` run references one hypothesis ID. Claude proposes status changes; the user confirms them.

### Runs

- Type `exploratory` or `final`; only `final` runs count as results. Ledger lines are never edited.
- Commit only the ledger, `final` `meta.json`, and results derived from `final` runs. Exploratory outputs may be deleted once logged, unless referenced in `STATUS.md`, `HYPOTHESES.md`, or a meeting summary. `final` outputs are never deleted.
- Runs over 15 minutes (`expected_runtime_minutes`, estimated by a pilot run if unknown) need user approval.

### Data

- Raw data is never changed after it is added. Every run and every processing step writes a new folder named with timestamp and parameter hash, containing its full parameter settings and metadata (runs via the runner, processing steps via `tools/output_folder.py`). Outputs are never edited or overwritten; a changed parameter or input means a new folder.
- Before processing a new dataset, ask for source, license, version, and human-participant involvement. Record the answers in its `ORIGIN.md` and in `DECISIONS.md`.
- Experiments with human participants: record ethics approval, consent, and anonymization in `docs/ETHICS.md` before data collection.

## Coding Standards

- **YAGNI**: build only what the task needs.
- **DRY**: extract shared infrastructure after the second duplication. Method variants stay separate.
- **Fail Fast**: explicit errors. No empty catch blocks, swallowed errors, or fallbacks that hide failures.
- **Simple First**: optimize only after profiling. Log optimizations that change numerical behavior.
- **Delete Aggressively**: remove dead code, except code that produced a logged result. Log removed method components.
- **Semantic Naming**: verbose, self-documenting names (`wait_until_obs_is_saved=true`, not `wait=true`). Method parameters named as in `METHOD.md`.
- **Tests**: each method component has a test on a hand-checkable instance and asserts its invariants.
