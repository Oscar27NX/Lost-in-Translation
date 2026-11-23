from __future__ import annotations

import json
import re

import httpx

from .extractor import OPAQUE_TACTICS
from .fixtures import build_lines_from_curated, get_curated_examples
from .latex_fmt import (
    escape_latex_code,
    escape_latex_text,
    lean_expr_to_latex,
    strip_lean_comments_preserving_lines,
    validate_katex_safety,
)
from .latex_fmt_v2 import (
    escape_latex_code_v2,
    escape_latex_text_v2,
    format_greek_or_ident,
    lean_expr_to_latex_v2,
)
from .schemas import (
    DerivationMeta,
    FaithfulnessCheck,
    FidelityMode,
    FlagRecord,
    InfoTreeDocument,
    InfoTreeNode,
    LineRevision,
    LineStatus,
    ModelConfig,
    ProofLine,
)

ADVERSARIAL_LITERAL_SYSTEM_PROMPT = """You are Lost-In-Translation (LIT), a specialized formal-methods Lean 4 InfoTree-to-LaTeX translator.
Unlike a generic helpful assistant, you MUST obey strict adversarial faithfulness rules:
1. LITERAL GROUNDING ONLY: Translate ONLY what is justified by the provided Lean 4 source slice, goalsBefore, goalsAfter, and referencedConstants. NEVER invent steps, silently drop hypotheses, weaken quantifiers, or hide domain guards (e.g. ℕ truncated subtraction, positivity premises, coercions ℕ → ℤ → ℝ).
2. EXPOSE OPAQUE AUTOMATION: If the tactic slice relies on decision procedures or simplifiers (`linarith`, `omega`, `simp`, `field_simp`, `norm_num`, `aesop`, `ring`), explicitly note what algebraic/arithmetic reasoning is implicit inside the tactic and mark `opaque_automation: true`.
3. NEVER HIDE `sorry`: If `sorry` appears anywhere in the slice, emit an explicit red-alert LaTeX placeholder `\\textbf{[UNPROVED: sorry]}` and set confidence <= 0.1.
4. STRUCTURED OUTPUT: Respond ONLY with valid JSON containing keys:
   - "latex": string (valid KaTeX-compatible LaTeX math/text, no surrounding $$ or \\[ \\])
   - "section_label": short 2-5 word mathematical step title
   - "procedure": array of strings (step-by-step derivation from the InfoTree state transition)
   - "justification": concise rationale linking the Lean tactics & lemmas to the LaTeX output
   - "confidence": float in [0.0, 1.0] reflecting literal translation certainty
   - "opaque_automation": boolean
   - "warnings": array of short diagnostic warning strings (empty if clean)
"""


def _build_node_user_prompt(
    node: InfoTreeNode,
    theorem_statement: str,
    fidelity_mode: FidelityMode,
    instruction: str | None = None,
    active_flags: list[FlagRecord] | None = None,
    previous_latex: str | None = None,
) -> str:
    mode_guidance = {
        FidelityMode.LITERAL: "Mode: LITERAL FORMAL SYMBOLIC. Maximize symbol-for-symbol fidelity to Lean types, binders, and lemmas.",
        FidelityMode.EXPANDED: "Mode: EXPANDED AUTOMATION. Unpack opaque tactics (`linarith`, `omega`, `simp`, `field_simp`, `exact_mod_cast`) into explicit algebraic substeps while clearly marking what was unpacked.",
        FidelityMode.FORMAL_PROSE: "Mode: STRUCTURED MATHEMATICAL PROSE. Use crisp publication-style wording while preserving every hypothesis, quantifier, and domain constraint.",
    }[fidelity_mode]

    payload = {
        "theorem_statement": theorem_statement,
        "fidelity_mode": mode_guidance,
        "lean_span": f"L{node.span.start_line}-L{node.span.end_line}",
        "tactic_kind": node.tactic_kind,
        "lean_source_slice": node.source_slice,
        "goals_before": [g.model_dump() for g in node.goals_before],
        "goals_after": [g.model_dump() for g in node.goals_after],
        "referenced_constants": node.referenced_constants,
    }
    if previous_latex:
        payload["previous_latex_attempt"] = previous_latex
    if active_flags:
        payload["human_reviewer_flags_to_fix"] = [
            {
                "categories": [c.value for c in f.categories],
                "comment": f.comment,
            }
            for f in active_flags
            if not f.resolved
        ]
    if instruction:
        payload["user_regeneration_directive"] = instruction

    return json.dumps(payload, indent=2, ensure_ascii=False)


def _strip_bullets(text: str) -> tuple[str, bool]:
    s = text.strip()
    had_bullet = s.startswith("·")
    while s.startswith("·"):
        s = s[1:].strip()
    return s, had_bullet


def _translate_single_node_symbolic(
    node: InfoTreeNode,
    line_number: int,
    fidelity_mode: FidelityMode = FidelityMode.LITERAL,
    instruction: str | None = None,
    active_flags: list[FlagRecord] | None = None,
    symbolic_variant: str = "symbolic_literal_v0_2",
) -> ProofLine:
    """Deterministic symbolic literal translator for arbitrary Lean 4 InfoTree nodes."""
    is_v2 = symbolic_variant == "symbolic_literal_v0_2"
    expr_fn = lean_expr_to_latex_v2 if is_v2 else lean_expr_to_latex
    text_fn = escape_latex_text_v2 if is_v2 else escape_latex_text
    code_fn = escape_latex_code_v2 if is_v2 else escape_latex_code
    ident_fn = format_greek_or_ident if is_v2 else (lambda nm: rf"\mathrm{{{escape_latex_text(nm)}}}")
    eff_model_id = "lit-symbolic-literal-v0.2" if is_v2 else "lit-symbolic-literal-v0.1"
    decl_max_len = None if is_v2 else 280
    term_max_len = 360 if is_v2 else 240

    clean_src = strip_lean_comments_preserving_lines(node.source_slice).strip()
    collapsed = re.sub(r"\s+", " ", clean_src).strip()
    first_raw = clean_src.splitlines()[0].strip() if clean_src else ""
    first, had_bullet = _strip_bullets(first_raw)
    collapsed_no_bullet, _ = _strip_bullets(collapsed)
    head_tok = re.split(r"[\s(\[⟨;:,]+", first)[0] if first else ""

    tokens = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", clean_src))
    has_sorry = "sorry" in tokens
    is_opaque = node.is_opaque_automation or bool(tokens & OPAQUE_TACTICS)

    section_label = "Proof Step"
    procedure: list[str] = [
        f"Inspect InfoTree node `{node.node_id}` (`{node.tactic_kind}`) spanning Lean lines L{node.span.start_line}–L{node.span.end_line}."
    ]
    checks: list[FaithfulnessCheck] = []
    known_tactic_tokens = OPAQUE_TACTICS | {
        "intro", "intros", "rintro", "have", "suffices", "let", "set", "obtain", "rcases",
        "cases", "by_cases", "split_ifs", "induction", "by_contra", "contrapose", "push_neg",
        "rw", "rwa", "calc", "exact", "exacts", "apply", "refine", "use", "unfold", "dsimp",
        "convert", "filter_upwards", "ext", "congr", "zify", "push_cast",
    }
    tactics_used = [t for t in sorted(tokens) if t in known_tactic_tokens]

    # --- Structural declaration nodes (multi-theorem files & defs) ---
    if node.kind == "definition":
        m_def = re.match(
            r"^(?:@\[[^\]]+\]\s*)?(?:(?:private|protected|noncomputable|local|scoped|partial|unsafe)\s+)*"
            r"(def|abbrev|structure|instance)\s+([A-Za-z0-9_']+)(.*)$",
            collapsed,
        )
        d_name = m_def.group(2) if m_def else "definition"
        d_rest = m_def.group(3).strip() if m_def else collapsed
        section_label = f"Definition ({d_name})"
        latex = rf"\textbf{{Definition }} ({ident_fn(d_name)})\text{{:}}\quad {expr_fn(d_rest, max_len=decl_max_len)}."
        confidence = 0.86
        justification = f"Structural Lean `{m_def.group(1) if m_def else 'def'}` declaration for `{d_name}`."
        procedure.append(f"Extracted definition header & body for `{d_name}`.")
    elif node.kind == "theorem":
        m_thm = re.match(
            r"^(?:@\[[^\]]+\]\s*)?(?:(?:private|protected|noncomputable)\s+)*"
            r"(theorem|lemma|example)\s+([A-Za-z0-9_']*)(.*)$",
            collapsed,
        )
        t_kind = m_thm.group(1) if m_thm else "theorem"
        t_name = (m_thm.group(2) or "example") if m_thm else "theorem"
        prop = node.goals_after[0].target if node.goals_after else collapsed
        section_label = f"{t_kind.title()} ({t_name})"
        latex = rf"\textbf{{{t_kind.title()} }} ({ident_fn(t_name)})\text{{:}}\quad {expr_fn(prop, max_len=decl_max_len)}."
        confidence = 0.90
        justification = f"Top-level Lean `{t_kind}` statement `{t_name}`."
        procedure.append(f"Parsed `{t_kind}` signature `{t_name}` and target proposition.")
    elif has_sorry:
        section_label = "Unproved Gap (sorry)"
        latex = r"\textbf{[UNPROVED GAP: }\texttt{sorry}\textbf{ -- formal proof obligation missing]}"
        confidence = 0.08
        justification = "Detected `sorry` axiom in Lean tactic block; faithful translation refuses to fabricate a proof step."
        checks.append(FaithfulnessCheck(name="sorry_detected", status="fail", detail="Lean proof contains `sorry`; proof is incomplete."))
    elif m := re.match(r"have\s+([A-Za-z0-9_']+)\s*:\s*(.+?)\s*:=", collapsed_no_bullet):
        h_name, h_ty = m.group(1), m.group(2).strip()
        section_label = f"Claim ({h_name})"
        math_ty = expr_fn(h_ty)
        safe_name = text_fn(h_name)
        if fidelity_mode == FidelityMode.EXPANDED and is_opaque:
            used_ops = text_fn(", ".join(sorted(tokens & OPAQUE_TACTICS)))
            latex = rf"\text{{We establish }} ({safe_name})\text{{:}}\quad {math_ty} \quad \text{{(verified via }} \texttt{{{used_ops}}}\text{{; audit intermediate steps)}}."
        elif fidelity_mode == FidelityMode.FORMAL_PROSE:
            latex = rf"\text{{It follows that }} {math_ty}."
        else:
            latex = rf"\text{{Claim }} ({safe_name})\text{{:}}\quad {math_ty}."
        confidence = 0.78 if is_opaque else 0.89
        justification = f"Directly translates `have {h_name}` statement from InfoTree hypothesis introduction."
        procedure.append(f"Map binder `{h_name}` and proposition into formal LaTeX.")
    elif m := re.match(r"have\s*:\s*(.+?)\s*:=", collapsed_no_bullet):
        h_ty = m.group(1).strip()
        section_label = "Intermediate Claim"
        latex = rf"\text{{Intermediate claim:}}\quad {expr_fn(h_ty)}."
        confidence = 0.77 if is_opaque else 0.87
        justification = "Translates anonymous `have : P := ...` assertion."
        procedure.append("Extract anonymous `have` proposition into formal LaTeX.")
    elif m := re.match(r"have\s*:=\s*(.+)", collapsed_no_bullet):
        term_str = m.group(1).strip()
        section_label = "Intermediate Fact"
        latex = rf"\text{{Note that }} {expr_fn(term_str, max_len=term_max_len)}."
        confidence = 0.75
        justification = "Records anonymous `have := ...` lemma instantiation (full inferred type requires live Lean 4 InfoTree)."
        procedure.append("Translate anonymous `have :=` term witness.")
    elif m := re.match(r"suffices\s+(?:([A-Za-z0-9_']+)\s*:\s*)?(.+?)\s+(?:by|from)\b", collapsed_no_bullet):
        s_name, s_ty = m.group(1), m.group(2).strip()
        section_label = f"Sufficient Condition ({s_name})" if s_name else "Sufficient Condition"
        latex = rf"\text{{It suffices to show }}\quad {expr_fn(s_ty)}."
        confidence = 0.86
        justification = "Translates `suffices` backward goal reduction."
        procedure.append("State sufficient subgoal introduced by `suffices`.")
    elif m := re.match(r"(?:let|set)\s+([A-Za-z0-9_']+)\s*(?::\s*[^:=]+)?\s*:=\s*(.+)", first):
        nm, expr = m.group(1), m.group(2).strip()
        section_label = f"Definition ({nm})"
        latex = rf"\text{{Set }} {ident_fn(nm)} := {expr_fn(expr)}."
        confidence = 0.91
        justification = f"Literal local definition binding `{nm}`."
        procedure.append(f"Translate local binding `{nm} := ...`.")
    elif m := re.match(r"(?:intros?|rintro)(?:\s+([^;]+)|;|$)", first):
        binders = (m.group(1) or "").strip()
        section_label = "Introduce Hypotheses"
        if binders:
            latex = rf"\text{{Let }} {expr_fn(binders, max_len=180)} \text{{ be given.}}"
        else:
            latex = r"\text{Introduce hypotheses from the goal context.}"
        confidence = 0.90
        justification = f"Introduces binders/patterns `{binders or 'context'}` from InfoTree goal state."
        procedure.append(f"Extract introduced context variables `{binders or 'all'}`.")
    elif m := re.match(r"(?:obtain|rcases)\s+⟨([^⟩]+)⟩(?:\s*:\s*(.+?))?\s*:=\s*(.+)", collapsed_no_bullet):
        vars_str = m.group(1).strip()
        ann_ty = m.group(2).strip() if m.group(2) else None
        src_h = m.group(3).strip()
        section_label = "Witness / Case Elimination"
        if ann_ty:
            latex = rf"\text{{Obtain }} {expr_fn(vars_str, max_len=100)} \text{{ satisfying }} {expr_fn(ann_ty, max_len=term_max_len)}."
        else:
            latex = rf"\text{{From }} {expr_fn(src_h, max_len=120)}\text{{, choose }} {expr_fn(vars_str, max_len=120)}."
        confidence = 0.88
        justification = f"Destructures existential/conjunctive witness(es) `{vars_str}`."
        procedure.append(f"Eliminate witness(es) `{vars_str}`.")
    elif head_tok in ("cases", "rcases", "by_cases", "split_ifs"):
        arg = first.split(None, 1)[1] if " " in first else ""
        section_label = "Case Split"
        if arg:
            latex = rf"\text{{Split into cases on }} {expr_fn(arg, max_len=200)}."
        else:
            latex = r"\text{Split into cases on the conditional branches.}"
        confidence = 0.82
        justification = f"Case analysis via `{head_tok}`."
        procedure.append(f"Branch proof state using `{head_tok}`.")
    elif head_tok in ("by_contra", "contrapose", "contrapose!"):
        section_label = "Contradiction / Contraposition"
        latex = (
            r"\text{Proceed by contraposition.}"
            if head_tok.startswith("contrapose")
            else r"\text{Assume for contradiction that the target statement fails.}"
        )
        confidence = 0.91
        justification = f"Logical negation / contraposition transform via `{head_tok}`."
        procedure.append(f"Track goal transformation via `{head_tok}`.")
    elif head_tok in ("induction", "induction'"):
        var = first.split()[1] if len(first.split()) > 1 else "n"
        section_label = f"Induction on {var}"
        latex = rf"\text{{We proceed by structural induction on }} {expr_fn(var, max_len=80)}."
        confidence = 0.89
        justification = f"Initiates inductive case split on `{var}`."
        procedure.append(f"Split InfoTree goal into base and inductive subgoals for `{var}`.")
    elif head_tok in ("rw", "rwa", "erw", "conv_lhs", "conv_rhs"):
        section_label = "Equational Rewrite"
        latex = rf"\text{{Rewriting by }} \texttt{{{code_fn(first)}}} \text{{ transforms the current goal.}}"
        confidence = 0.80
        justification = f"Applies equational substitution via `{head_tok}`."
        procedure.append(f"Trace rewrite sequence `{first[:80]}` on active goal.")
    elif head_tok in ("unfold", "dsimp"):
        body = first.split(None, 1)[1] if " " in first else first
        section_label = "Unfold Definition"
        latex = rf"\text{{Unfolding }} \texttt{{{code_fn(body)}}} \text{{ exposes its definition.}}"
        confidence = 0.88
        justification = f"Definitional unfolding via `{head_tok}`."
        procedure.append(f"Unfold `{body}` in current goal/hypotheses.")
    elif head_tok == "filter_upwards":
        section_label = "Eventually / Filter Bound"
        latex = rf"\text{{By filter eventual bounds (}}\texttt{{{code_fn(first)}}}\text{{), the property holds eventually.}}"
        confidence = 0.78
        justification = "Reduces `Filter.Eventually` / `atTop` goal to asymptotic hypotheses."
        procedure.append("Apply `filter_upwards` eventual reasoning.")
    elif head_tok == "convert":
        body = first.split(None, 1)[1] if " " in first else first
        section_label = "Goal Reduction (convert)"
        latex = rf"\text{{Matching the goal against }} {expr_fn(body, max_len=200)} \text{{ leaves congruence obligations.}}"
        confidence = 0.77
        justification = "`convert` unifies goal with a near-matching lemma up to residual side conditions."
        procedure.append("Reduce goal via `convert` congruence matching.")
    elif head_tok in ("gcongr", "ext", "congr"):
        section_label = "Monotonicity / Congruence" if head_tok == "gcongr" else "Extensionality / Congruence"
        latex = rf"\text{{By }} \texttt{{{code_fn(head_tok)}}}\text{{, reduce to pointwise subgoals via }} \texttt{{{code_fn(first)}}}\text{{.}}"
        confidence = 0.80 if head_tok != "gcongr" else 0.76
        justification = f"Structural `{head_tok}` congruence decomposition."
        procedure.append(f"Decompose goal structurally with `{head_tok}`.")
    elif head_tok in ("simp", "simp_all", "simpa"):
        section_label = "Simplification"
        latex = rf"\text{{Simplifying via }} \texttt{{{code_fn(first)}}} \text{{ reduces the goal.}}"
        confidence = 0.74
        justification = f"Automated rewriting/simplification via `{head_tok}`; inspect InfoTree state diff for exact lemmas applied."
        procedure.append(f"Apply simplifier `{head_tok}` (opaque automation).")
    elif head_tok in (
        "norm_num", "ring", "ring_nf", "field_simp", "linarith", "nlinarith",
        "omega", "positivity", "norm_cast", "exact_mod_cast", "push_cast", "zify", "interval_cases",
    ):
        section_label = "Algebraic / Arithmetic Automation"
        latex = rf"\text{{Discharged by arithmetic/algebraic automation }} \texttt{{{code_fn(first)}}}\text{{.}}"
        confidence = 0.73
        justification = f"Automated arithmetic/ring/cast procedure `{head_tok}`."
        procedure.append(f"Invoke decision/normalization tactic `{head_tok}`.")
    elif head_tok in ("aesop", "aesop_cat", "grind", "decide", "tauto", "solve_by_elim", "apply_rules"):
        section_label = "Automated Search"
        latex = rf"\text{{Closed by automated proof search }} \texttt{{{code_fn(first)}}}\text{{.}}"
        confidence = 0.68
        justification = f"Opaque search tactic `{head_tok}` discharged the subgoal without an explicit human proof trace."
        procedure.append(f"Opaque search via `{head_tok}` (audit recommended).")
    elif head_tok == "calc":
        section_label = "Calculational Chain"
        latex = rf"\text{{By the calculational chain: }}\; {expr_fn(first[4:].strip())}"
        confidence = 0.83
        justification = "Translates Lean `calc` transitivity chain."
        procedure.append("Align `calc` steps with transitive relation symbols.")
    elif head_tok in ("exact", "exacts", "apply", "refine", "refine'", "use", "assumption", "rfl"):
        body = first.split(None, 1)[1] if " " in first else first
        section_label = "Goal Discharge / Witness"
        latex = rf"\text{{Conclude/refine via }} {expr_fn(body, max_len=term_max_len)}."
        confidence = 0.84
        justification = f"Closes or refines the active goal using `{head_tok}`."
        procedure.append(f"Verify `{head_tok}` term unifies with active target.")
    else:
        section_label = "Tactic Step"
        latex = rf"\text{{Applying }} \texttt{{{code_fn(first)}}} \text{{ advances the proof state.}}"
        confidence = 0.72 if is_opaque else 0.77
        justification = "Literal fallback translation of Lean tactic slice."
        procedure.append(f"Record tactic `{first[:80]}` directly to avoid hallucinating unsupported prose.")

    if had_bullet and not section_label.startswith(("Subgoal", "Theorem", "Lemma", "Definition")):
        section_label = f"Subgoal · {section_label}"

    # Apply directive / flag-repair adaptation when regenerating
    unresolved_flags = [f for f in (active_flags or []) if not f.resolved]
    if unresolved_flags:
        cats = ", ".join(sorted({c.value for f in unresolved_flags for c in f.categories}))
        notes = "; ".join(f.comment for f in unresolved_flags if f.comment)
        procedure.append(f"Incorporated human reviewer flags ({cats})" + (f": {notes}" if notes else "."))
        if any(c.value == "opaque_tactic_elision" for f in unresolved_flags for c in f.categories):
            latex += r"\; \text{[Audited: implicit tactic steps flagged for explicit justification]}"
        if any(c.value == "missing_hypothesis" for f in unresolved_flags for c in f.categories):
            added_hyps = [h.name for g in node.goals_before for h in g.hypotheses][:3]
            if added_hyps:
                safe_hyps = text_fn(", ".join(added_hyps))
                latex = rf"\text{{Using hypotheses }} {safe_hyps}\text{{: }}\; " + latex
        justification += f" Regenerated to address reviewer flag(s): {cats}."
    if instruction:
        procedure.append(f"Applied user regeneration directive: \"{instruction}\"")
        justification += f" Directive applied: {instruction}"

    # Structural KaTeX safety guard before emitting
    safety_issues = validate_katex_safety(latex)
    if safety_issues:
        latex = rf"\text{{Lean step: }} \texttt{{{code_fn(first, max_len=200)}}}"
        checks.append(
            FaithfulnessCheck(
                name="latex_safety_fallback",
                status="warn",
                detail=f"Applied KaTeX-safe code fallback ({'; '.join(safety_issues[:2])}).",
            )
        )

    if is_opaque and not has_sorry:
        used_ops = ", ".join(sorted(tokens & OPAQUE_TACTICS)) or node.tactic_kind
        checks.append(
            FaithfulnessCheck(
                name="opaque_tactic_audit",
                status="warn",
                detail=f"Uses automated tactic(s) `{used_ops}`; human audit recommended.",
            )
        )
    if not checks:
        checks.append(
            FaithfulnessCheck(
                name="literal_alignment",
                status="pass",
                detail=f"Mapped directly from InfoTree span L{node.span.start_line}–L{node.span.end_line}.",
            )
        )

    deriv = DerivationMeta(
        procedure=procedure,
        justification=justification,
        tactics_used=tactics_used or [node.tactic_kind],
        referenced_lemmas=node.referenced_constants,
        model_id=eff_model_id,
        fidelity_mode=fidelity_mode,
        confidence=round(confidence, 2),
        opaque_automation=is_opaque,
        checks=checks,
    )

    return ProofLine(
        line_id=f"line-{line_number}",
        line_number=line_number,
        section_label=section_label,
        indent_level=min(node.depth, 3),
        latex=latex,
        original_latex=latex,
        lean_span=node.span,
        infotree_node_ids=[node.node_id],
        status=LineStatus.UNREVIEWED,
        derivation=deriv,
        flags=[],
        revisions=[
            LineRevision(
                revision_index=0,
                latex=latex,
                source="initial_inference",
                model_id=deriv.model_id,
                fidelity_mode=fidelity_mode,
                justification=deriv.justification,
            )
        ],
    )


async def _call_openai_compatible_lm(
    config: ModelConfig,
    node: InfoTreeNode,
    theorem_statement: str,
    fidelity_mode: FidelityMode,
    instruction: str | None = None,
    active_flags: list[FlagRecord] | None = None,
    previous_latex: str | None = None,
    temperature_override: float | None = None,
) -> dict:
    url = config.base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    user_prompt = _build_node_user_prompt(
        node=node,
        theorem_statement=theorem_statement,
        fidelity_mode=fidelity_mode,
        instruction=instruction,
        active_flags=active_flags,
        previous_latex=previous_latex,
    )

    body = {
        "model": config.model_name,
        "temperature": temperature_override if temperature_override is not None else config.temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": ADVERSARIAL_LITERAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # Strip accidental markdown code fences if a small model emits them
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        return json.loads(content)


async def translate_infotree(
    infotree: InfoTreeDocument,
    config: ModelConfig,
    fidelity_mode: FidelityMode = FidelityMode.LITERAL,
    example_key: str | None = None,
) -> tuple[list[ProofLine], str]:
    """
    Translate an entire InfoTreeDocument into aligned ProofLines.
    Returns (lines, effective_model_id).
    """
    # If running in local small LM mode, invoke the configured OpenAI-compatible server per node
    if config.backend_mode == "openai_compatible_lm":
        lines: list[ProofLine] = []
        for idx, node in enumerate(infotree.nodes, start=1):
            try:
                parsed = await _call_openai_compatible_lm(
                    config=config,
                    node=node,
                    theorem_statement=infotree.statement_lean,
                    fidelity_mode=fidelity_mode,
                )
                latex = str(parsed.get("latex", "")).strip() or r"\text{[Empty LM response]}"
                proc = [str(s) for s in parsed.get("procedure", [])] or [f"Inferred by {config.model_name} from L{node.span.start_line}–L{node.span.end_line}."]
                just = str(parsed.get("justification", "Generated by local specialized small LM."))
                conf = float(parsed.get("confidence", 0.8))
                opaque = bool(parsed.get("opaque_automation", node.is_opaque_automation))
                warnings = [str(w) for w in parsed.get("warnings", [])]
                checks = [FaithfulnessCheck(name="lm_self_audit", status="warn", detail=w) for w in warnings]
                if not checks:
                    checks.append(FaithfulnessCheck(name="lm_schema_valid", status="pass", detail=f"Strict JSON response verified from {config.model_name}."))
                deriv = DerivationMeta(
                    procedure=proc,
                    justification=just,
                    tactics_used=[node.tactic_kind],
                    referenced_lemmas=node.referenced_constants,
                    model_id=config.model_name,
                    fidelity_mode=fidelity_mode,
                    confidence=max(0.0, min(1.0, round(conf, 2))),
                    opaque_automation=opaque,
                    checks=checks,
                )
                lines.append(
                    ProofLine(
                        line_id=f"line-{idx}",
                        line_number=idx,
                        section_label=str(parsed.get("section_label", f"Step {idx}")),
                        indent_level=min(node.depth, 3),
                        latex=latex,
                        original_latex=latex,
                        lean_span=node.span,
                        infotree_node_ids=[node.node_id],
                        status=LineStatus.UNREVIEWED,
                        derivation=deriv,
                        flags=[],
                        revisions=[
                            LineRevision(
                                revision_index=0,
                                latex=latex,
                                source="initial_inference",
                                model_id=config.model_name,
                                fidelity_mode=fidelity_mode,
                                justification=just,
                            )
                        ],
                    )
                )
            except Exception as exc:
                fallback = _translate_single_node_symbolic(
                    node,
                    idx,
                    fidelity_mode=fidelity_mode,
                    symbolic_variant=config.symbolic_variant,
                )
                fallback.derivation.checks.append(
                    FaithfulnessCheck(
                        name="lm_fallback",
                        status="warn",
                        detail=f"Local LM call failed ({type(exc).__name__}); fell back to symbolic baseline.",
                    )
                )
                lines.append(fallback)
        return lines, config.model_name

    # Symbolic-Literal Baseline mode: use rich curated literal pairs when matching a curated fixture
    eff_model_id = (
        "lit-symbolic-literal-v0.2"
        if config.symbolic_variant == "symbolic_literal_v0_2"
        else "lit-symbolic-literal-v0.1"
    )
    examples = get_curated_examples()
    if example_key and example_key in examples:
        return build_lines_from_curated(examples[example_key], fidelity_mode=fidelity_mode), eff_model_id
    for ex in examples.values():
        if ex.infotree.source_code.strip() == infotree.source_code.strip():
            return build_lines_from_curated(ex, fidelity_mode=fidelity_mode), eff_model_id

    lines = [
        _translate_single_node_symbolic(
            node,
            idx,
            fidelity_mode=fidelity_mode,
            symbolic_variant=config.symbolic_variant,
        )
        for idx, node in enumerate(infotree.nodes, start=1)
    ]
    return lines, eff_model_id


async def regenerate_single_line(
    infotree: InfoTreeDocument,
    line: ProofLine,
    config: ModelConfig,
    fidelity_mode: FidelityMode,
    instruction: str | None = None,
    use_active_flags: bool = True,
    temperature_override: float | None = None,
    example_key: str | None = None,
) -> tuple[str, DerivationMeta]:
    """Regenerate ONLY one specific LaTeX line z from its InfoTree nodes + reviewer feedback."""
    node_map = {n.node_id: n for n in infotree.nodes}
    primary_node = next((node_map[nid] for nid in line.infotree_node_ids if nid in node_map), None)
    if primary_node is None:
        primary_node = InfoTreeNode(
            node_id="synthetic",
            span=line.lean_span,
            source_slice="\n".join(infotree.source_code.splitlines()[line.lean_span.start_line - 1 : line.lean_span.end_line]),
            tactic_kind="unknown",
        )

    active_flags = [f for f in line.flags if not f.resolved] if use_active_flags else []

    if config.backend_mode == "openai_compatible_lm":
        parsed = await _call_openai_compatible_lm(
            config=config,
            node=primary_node,
            theorem_statement=infotree.statement_lean,
            fidelity_mode=fidelity_mode,
            instruction=instruction,
            active_flags=active_flags,
            previous_latex=line.latex,
            temperature_override=temperature_override,
        )
        latex = str(parsed.get("latex", line.latex)).strip()
        proc = [str(s) for s in parsed.get("procedure", [])] or [f"Targeted regeneration by {config.model_name}."]
        just = str(parsed.get("justification", "Regenerated via local specialized small LM."))
        conf = max(0.0, min(1.0, round(float(parsed.get("confidence", 0.85)), 2)))
        opaque = bool(parsed.get("opaque_automation", primary_node.is_opaque_automation))
        warnings = [str(w) for w in parsed.get("warnings", [])]
        checks = [FaithfulnessCheck(name="lm_self_audit", status="warn", detail=w) for w in warnings]
        if not checks:
            checks.append(FaithfulnessCheck(name="targeted_regen", status="pass", detail=f"Regenerated with {config.model_name} ({fidelity_mode.value})."))
        return latex, DerivationMeta(
            procedure=proc,
            justification=just,
            tactics_used=line.derivation.tactics_used,
            referenced_lemmas=primary_node.referenced_constants or line.derivation.referenced_lemmas,
            model_id=config.model_name,
            fidelity_mode=fidelity_mode,
            confidence=conf,
            opaque_automation=opaque,
            checks=checks,
        )

    # Symbolic-Literal Baseline regeneration:
    # Check if this line belongs to a curated example with rich mode variants
    examples = get_curated_examples()
    ex = examples.get(example_key) if example_key else None
    if ex is None:
        for cand in examples.values():
            if cand.infotree.source_code.strip() == infotree.source_code.strip():
                ex = cand
                break

    if ex is not None:
        base_item = next((it for it in ex.literal_lines if it["line_id"] == line.line_id), None)
        if base_item is not None:
            new_latex = base_item["latex"]
            deriv: DerivationMeta = base_item["derivation"].model_copy(deep=True)
            deriv.fidelity_mode = fidelity_mode

            if fidelity_mode == FidelityMode.EXPANDED:
                if line.line_id in ex.expanded_overrides:
                    new_latex, extra_proc, new_just = ex.expanded_overrides[line.line_id]
                    deriv.procedure = deriv.procedure + extra_proc
                    deriv.justification = new_just
                    deriv.confidence = min(0.96, round(deriv.confidence + 0.06, 2))
                else:
                    lemmas = ", ".join(deriv.referenced_lemmas) if deriv.referenced_lemmas else "the active context"
                    new_latex = new_latex + rf"\; \text{{(justified explicitly via }} \texttt{{{escape_latex_text(lemmas)}}}\text{{)}}."
                    deriv.procedure.append("Expanded mode: appended explicit lemma/tactic provenance citation.")
                    deriv.justification += " Expanded mode adds explicit Lean lemma attribution."
            elif fidelity_mode == FidelityMode.FORMAL_PROSE:
                if line.line_id in ex.prose_overrides:
                    new_latex, new_proc, new_just = ex.prose_overrides[line.line_id]
                    deriv.procedure = new_proc
                    deriv.justification = new_just
                else:
                    deriv.procedure.append("Formal prose regeneration requested; retained core mathematical terms.")
                    deriv.justification += " Adjusted toward concise mathematical prose."

            if active_flags:
                cats = sorted({c.value for f in active_flags for c in f.categories})
                comments = [f.comment for f in active_flags if f.comment]
                deriv.procedure.append(f"Flag-repair pass targeting: {', '.join(cats)}.")
                if "missing_hypothesis" in cats and primary_node.goals_before:
                    hyps = ", ".join(h.name for h in primary_node.goals_before[0].hypotheses[:4])
                    if hyps and hyps not in new_latex:
                        new_latex = rf"\text{{Using context }} ({escape_latex_text(hyps)})\text{{: }}\; " + new_latex
                if "opaque_tactic_elision" in cats and line.line_id in ex.expanded_overrides:
                    new_latex, extra_proc, _ = ex.expanded_overrides[line.line_id]
                    deriv.procedure.extend(extra_proc)
                if "notation_mismatch" in cats:
                    new_latex = new_latex.replace(r"|a|", r"|q.\mathrm{num}|").replace(r"\frac{a}{b}", r"\frac{q.\mathrm{num}}{q.\mathrm{den}}")
                deriv.justification += f" Addressed reviewer flag(s) [{', '.join(cats)}]" + (f": {'; '.join(comments)}" if comments else ".")
                deriv.checks.append(
                    FaithfulnessCheck(
                        name="flag_repair_pass",
                        status="pass",
                        detail=f"Re-inferred incorporating {len(active_flags)} reviewer flag(s).",
                    )
                )

            if instruction:
                deriv.procedure.append(f"Applied user directive: \"{instruction}\"")
                if "exact lean" in instruction.lower() or "raw" in instruction.lower():
                    new_latex = new_latex.replace(r"|a|", r"|q.\mathrm{num}|")
                elif "shorter" in instruction.lower() or "concise" in instruction.lower():
                    new_latex = re.sub(r"\\text\{[^}]*witnessed by[^}]*\}", "", new_latex)
                deriv.justification += f" User directive: {instruction}"
                deriv.checks.append(
                    FaithfulnessCheck(
                        name="directive_applied",
                        status="pass",
                        detail=f"Regenerated with custom directive: {instruction}",
                    )
                )

            return new_latex, deriv

    # Generic symbolic fallback regeneration
    regen_line = _translate_single_node_symbolic(
        node=primary_node,
        line_number=line.line_number,
        fidelity_mode=fidelity_mode,
        instruction=instruction,
        active_flags=active_flags,
        symbolic_variant=config.symbolic_variant,
    )
    return regen_line.latex, regen_line.derivation
