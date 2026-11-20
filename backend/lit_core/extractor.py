from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .fixtures import REPO_ROOT, get_curated_examples
from .latex_fmt import lean_expr_to_latex, strip_lean_comments_preserving_lines
from .schemas import GoalState, Hypothesis, InfoTreeDocument, InfoTreeNode, Span

# Keep backwards-compatible alias for internal/external imports
_lean_expr_to_basic_latex = lean_expr_to_latex

OPAQUE_TACTICS = {
    "linarith",
    "nlinarith",
    "omega",
    "simp",
    "simp_all",
    "simpa",
    "aesop",
    "aesop_cat",
    "grind",
    "ring",
    "ring_nf",
    "field_simp",
    "norm_num",
    "positivity",
    "decide",
    "tauto",
    "exact_mod_cast",
    "norm_cast",
    "mod_cast",
    "push_cast",
    "zify",
    "gcongr",
    "interval_cases",
    "solve_by_elim",
    "apply_rules",
    "bv_decide",
    "sorry",
}

TACTIC_STARTERS = (
    "intro",
    "intros",
    "rintro",
    "have",
    "suffices",
    "let",
    "set",
    "obtain",
    "rcases",
    "cases",
    "by_cases",
    "split_ifs",
    "induction",
    "induction'",
    "by_contra",
    "contrapose",
    "push_neg",
    "rw",
    "rwa",
    "simp",
    "simp_all",
    "simpa",
    "calc",
    "exact",
    "exacts",
    "apply",
    "refine",
    "refine'",
    "use",
    "constructor",
    "convert",
    "filter_upwards",
    "gcongr",
    "ext",
    "congr",
    "linarith",
    "nlinarith",
    "omega",
    "ring",
    "ring_nf",
    "field_simp",
    "norm_num",
    "positivity",
    "grind",
    "aesop",
    "contradiction",
    "unfold",
    "dsimp",
    "zify",
    "push_cast",
    "norm_cast",
    "sorry",
)

_DECL_START_RE = re.compile(
    r"^(@\[[^\]]+\]\s*)?"
    r"(?:(?:private|protected|noncomputable|local|scoped|partial|unsafe)\s+)*"
    r"(theorem|lemma|example|def|abbrev|structure|instance)\b"
    r"(?:\s+([A-Za-z_][A-Za-z0-9_']*))?"
)

_SKIP_TOP_PREFIXES = (
    "import ",
    "open ",
    "namespace ",
    "end ",
    "section ",
    "set_option ",
    "variable ",
    "universe ",
    "attribute ",
    "termination_by ",
    "decreasing_by ",
    "#check",
    "#eval",
    "#print",
    "notation",
    "infix",
    "macro",
)


def is_lean_available() -> bool:
    return shutil.which("lake") is not None and shutil.which("lean") is not None


def _split_top_level_colon(sig: str) -> tuple[str, str]:
    """Split `binders : prop` at the first `:` at delimiter depth 0 (excluding `:=`)."""
    depth = 0
    i = 0
    n = len(sig)
    while i < n:
        ch = sig[i]
        if ch in "([{⟨":
            depth += 1
        elif ch in ")]}⟩" and depth > 0:
            depth -= 1
        elif ch == ":" and depth == 0:
            if i + 1 < n and sig[i + 1] == "=":
                i += 2
                continue
            return sig[:i].strip(), sig[i + 1 :].strip()
        i += 1
    return "", sig.strip()


def _extract_binders(binders_str: str) -> list[Hypothesis]:
    hyps: list[Hypothesis] = []
    for names_str, ty in re.findall(r"[(\[{]([A-Za-z0-9_ ']+)\s*:\s*([^)\]}]+)[)\]}]", binders_str):
        for nm in names_str.split():
            if nm and nm != "_":
                hyps.append(Hypothesis(name=nm.strip(), type=ty.strip(), change="unchanged"))
    return hyps


def _parse_theorem_header(source_code: str) -> tuple[str, str, str]:
    clean = strip_lean_comments_preserving_lines(source_code)
    matches = list(
        re.finditer(
            r"(?:^|\n)\s*(?:@\[[^\]]+\]\s*)?(?:(?:private|protected|noncomputable)\s+)*"
            r"(theorem|lemma|example)\s+([A-Za-z0-9_']*)\s*(.*?)\s*:=\s*by\b",
            clean,
            flags=re.DOTALL,
        )
    )
    if not matches:
        return ("custom_proof", "theorem custom_proof", r"\text{Custom Lean 4 Proof}")
    # For multi-theorem files (e.g. a library leading up to theorem_1_2), highlight the final main theorem
    match = matches[-1]
    kind = match.group(1)
    name = match.group(2) or "anonymous_example"
    sig_clean = re.sub(r"\s+", " ", match.group(3)).strip()
    stmt_lean = f"{kind} {name} {sig_clean}".strip()
    _, prop = _split_top_level_colon(sig_clean)
    stmt_latex = lean_expr_to_latex(prop)
    return (name, stmt_lean, stmt_latex)


def try_extract_via_lean4(source_code: str) -> InfoTreeDocument | None:
    """Invoke the compiled Lean 4 `infotree_dumper` binary if Lean 4 + Lake are available."""
    if not is_lean_available():
        return None
    extractor_dir = REPO_ROOT / "lean_extractor"
    if not (extractor_dir / "lakefile.toml").exists():
        return None

    with tempfile.NamedTemporaryFile(mode="w", suffix=".lean", delete=False, encoding="utf-8") as tmp:
        tmp.write(source_code)
        tmp_path = Path(tmp.name)

    try:
        proc = subprocess.run(
            ["lake", "exe", "infotree_dumper", str(tmp_path)],
            cwd=str(extractor_dir),
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        raw = json.loads(proc.stdout)
        nodes: list[InfoTreeNode] = []
        for item in raw.get("nodes", []):
            slice_txt = item.get("sourceSlice", "")
            head = slice_txt.split()[0] if slice_txt.split() else ""
            opaque = any(op in slice_txt for op in OPAQUE_TACTICS)
            nodes.append(
                InfoTreeNode(
                    node_id=item["nodeId"],
                    parent_id=item.get("parentId"),
                    depth=item.get("depth", 0),
                    kind=item.get("kind", "tactic"),
                    tactic_kind=item.get("tacticKind", head),
                    span=Span(
                        start_line=max(1, int(item.get("startLine", 1))),
                        end_line=max(1, int(item.get("endLine", 1))),
                        start_col=max(1, int(item.get("startCol", 1))),
                        end_col=max(1, int(item.get("endCol", 1))),
                    ),
                    source_slice=slice_txt,
                    goals_before=[
                        GoalState(
                            tag=g.get("tag", ""),
                            hypotheses=[Hypothesis(name=h["name"], type=h["type"]) for h in g.get("hypotheses", [])],
                            target=g.get("target", ""),
                            pretty=g.get("pretty", ""),
                        )
                        for g in item.get("goalsBefore", [])
                    ],
                    goals_after=[
                        GoalState(
                            tag=g.get("tag", ""),
                            hypotheses=[Hypothesis(name=h["name"], type=h["type"]) for h in g.get("hypotheses", [])],
                            target=g.get("target", ""),
                            pretty=g.get("pretty", ""),
                        )
                        for g in item.get("goalsAfter", [])
                    ],
                    referenced_constants=item.get("referencedConstants", []),
                    is_opaque_automation=opaque,
                )
            )
        if not nodes:
            return None
        thm_name, stmt_lean, stmt_latex = _parse_theorem_header(source_code)
        return InfoTreeDocument(
            theorem_name=thm_name,
            statement_lean=stmt_lean,
            statement_latex=stmt_latex,
            source_code=source_code,
            lean_version=raw.get("leanVersion", "4.12.0"),
            extractor_mode="lean4_infotree",
            nodes=nodes,
        )
    except Exception:
        return None
    finally:
        tmp_path.unlink(missing_ok=True)


def _strip_leading_bullets(text: str) -> tuple[str, int]:
    """Strip leading Lean `·` subgoal bullets and return (remaining_text, bullet_count)."""
    s = text.strip()
    count = 0
    while s.startswith("·"):
        count += 1
        s = s[1:].strip()
    return s, count


def _delim_delta(line: str) -> int:
    delta = 0
    for ch in line:
        if ch in "([⟨{":
            delta += 1
        elif ch in ")]⟩}":
            delta -= 1
    return delta


def extract_infotree_heuristic(source_code: str) -> InfoTreeDocument:
    """
    Deterministic fallback InfoTree extractor when local Lean 4 toolchain is unavailable.
    Strips nested block and line comments without changing line numbers, handles multi-theorem
    files and `def`/`abbrev` blocks, respects Lean `·` bullets and unbalanced delimiters, and
    emits InfoTreeNodes tagged with `extractor_mode = 'heuristic_parser'`.
    """
    thm_name, stmt_lean, stmt_latex = _parse_theorem_header(source_code)
    clean_source = strip_lean_comments_preserving_lines(source_code)

    raw_lines = source_code.splitlines()
    clean_lines = clean_source.splitlines()
    while len(clean_lines) < len(raw_lines):
        clean_lines.append("")
    n = len(raw_lines)

    # Count theorem/lemma/example declarations to decide whether to emit structural theorem headers
    theorem_count = sum(
        1
        for k in range(n)
        if (len(raw_lines[k]) - len(raw_lines[k].lstrip(" "))) == 0
        and (dm := _DECL_START_RE.match(clean_lines[k].strip()))
        and dm.group(2) in ("theorem", "lemma", "example")
    )

    nodes: list[InfoTreeNode] = []
    node_idx = 0
    mode = "top"
    base_indent: int | None = None
    current_hyps: list[Hypothesis] = []
    current_target = "Goal"

    def next_id() -> str:
        nonlocal node_idx
        node_idx += 1
        return f"h{node_idx}"

    i = 0
    while i < n:
        raw = raw_lines[i]
        clean = clean_lines[i]
        clean_strip = clean.strip()
        indent = len(raw) - len(raw.lstrip(" "))

        if mode == "top":
            if not clean_strip or clean_strip.startswith(_SKIP_TOP_PREFIXES) or clean_strip in ("end", "section"):
                i += 1
                continue

            dm = _DECL_START_RE.match(clean_strip) if indent == 0 else None
            if dm:
                decl_kind = dm.group(2)
                decl_name = dm.group(3) or "anonymous"

                if decl_kind in ("theorem", "lemma", "example"):
                    j = i
                    found_by = False
                    while j < n:
                        c_j = clean_lines[j]
                        if re.search(r":=\s*by\b", c_j):
                            found_by = True
                            break
                        if j > i:
                            r_j_indent = len(raw_lines[j]) - len(raw_lines[j].lstrip(" "))
                            if r_j_indent == 0 and c_j.strip() and _DECL_START_RE.match(c_j.strip()):
                                j -= 1
                                break
                        j += 1

                    end_hdr = min(j, n - 1)
                    hdr_clean = " ".join(clean_lines[k].strip() for k in range(i, end_hdr + 1))
                    hdr_raw = "\n".join(raw_lines[i : end_hdr + 1]).strip()

                    # Extract header binders & goal proposition
                    hdr_body = re.sub(r"^.*?:\s*", "", hdr_clean, count=1) if ":" in hdr_clean else hdr_clean
                    # Better: parse after decl_name up to `:= by`
                    after_name_m = re.search(
                        rf"\b{decl_kind}\b(?:\s+{re.escape(decl_name)})?(.*?)(?::=\s*by\b|$)",
                        hdr_clean,
                    )
                    sig_part = after_name_m.group(1).strip() if after_name_m else hdr_body
                    binders_part, target_part = _split_top_level_colon(sig_part)
                    current_hyps = _extract_binders(binders_part)
                    current_target = target_part or "Goal"

                    if theorem_count > 1:
                        refs = sorted(set(re.findall(r"\b[A-Z][A-Za-z0-9_]*\.[A-Za-z0-9_.]+\b", hdr_clean)))
                        nodes.append(
                            InfoTreeNode(
                                node_id=next_id(),
                                depth=0,
                                kind="theorem",
                                tactic_kind=f"decl.{decl_kind}",
                                span=Span(start_line=i + 1, end_line=end_hdr + 1, start_col=1, end_col=80),
                                source_slice=hdr_raw,
                                goals_before=[],
                                goals_after=[
                                    GoalState(
                                        tag=decl_name,
                                        hypotheses=list(current_hyps),
                                        target=current_target,
                                    )
                                ],
                                referenced_constants=refs,
                                is_opaque_automation=False,
                            )
                        )

                    if found_by:
                        mode = "proof"
                        base_indent = None
                        i = end_hdr + 1
                    else:
                        # Term-mode declaration: skip indented continuation lines
                        k = end_hdr + 1
                        while k < n:
                            ck = clean_lines[k].strip()
                            rk_indent = len(raw_lines[k]) - len(raw_lines[k].lstrip(" "))
                            if ck and rk_indent == 0 and (_DECL_START_RE.match(ck) or ck.startswith(_SKIP_TOP_PREFIXES) or ck in ("end", "section")):
                                break
                            k += 1
                        i = k
                    continue

                # Non-theorem declaration: `def`, `abbrev`, `structure`, `instance`
                j = i + 1
                last_nonempty = i
                while j < n:
                    ck = clean_lines[j].strip()
                    rk_indent = len(raw_lines[j]) - len(raw_lines[j].lstrip(" "))
                    if ck:
                        if rk_indent == 0 and not ck.startswith(("|", "where", "deriving", "termination_by", "decreasing_by")):
                            break
                        last_nonempty = j
                    j += 1

                def_raw = "\n".join(raw_lines[i : last_nonempty + 1]).strip()
                def_clean = "\n".join(clean_lines[i : last_nonempty + 1]).strip()
                refs = sorted(set(re.findall(r"\b[A-Z][A-Za-z0-9_]*\.[A-Za-z0-9_.]+\b", def_clean)))
                tokens = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", def_clean))
                nodes.append(
                    InfoTreeNode(
                        node_id=next_id(),
                        depth=0,
                        kind="definition",
                        tactic_kind=f"decl.{decl_kind}",
                        span=Span(start_line=i + 1, end_line=last_nonempty + 1, start_col=1, end_col=80),
                        source_slice=def_raw,
                        goals_before=[],
                        goals_after=[GoalState(tag=decl_name, hypotheses=[], target=def_clean)],
                        referenced_constants=refs,
                        is_opaque_automation=bool(tokens & OPAQUE_TACTICS),
                    )
                )
                i = j
                continue

            i += 1
            continue

        # --- mode == "proof" ---
        if not clean_strip:
            i += 1
            continue

        if indent == 0 and (
            _DECL_START_RE.match(clean_strip)
            or clean_strip.startswith(_SKIP_TOP_PREFIXES)
            or clean_strip in ("end", "section")
        ):
            mode = "top"
            continue

        if base_indent is None:
            base_indent = indent

        tactic_clean, bullet_count = _strip_leading_bullets(clean_strip)
        if not tactic_clean:
            i += 1
            continue

        start_ln = i + 1
        end_ln = start_ln
        chunk_raw = [raw]
        chunk_clean = [clean]
        balance = _delim_delta(clean)
        opens_subproof = tactic_clean.endswith((":= by", "by", ":=", "=>")) or tactic_clean.startswith("calc ")

        j = i + 1
        if balance > 0:
            while j < n and balance > 0:
                cj = clean_lines[j]
                rj = raw_lines[j]
                rj_indent = len(rj) - len(rj.lstrip(" "))
                if cj.strip() and rj_indent == 0 and _DECL_START_RE.match(cj.strip()):
                    break
                chunk_raw.append(rj)
                chunk_clean.append(cj)
                end_ln = j + 1
                balance += _delim_delta(cj)
                j += 1

        if opens_subproof or (j < n and j > i + 1 and clean_lines[j - 1].strip().endswith((":= by", "by", ":=", "=>"))):
            while j < n:
                rj = raw_lines[j]
                cj = clean_lines[j]
                if not rj.strip():
                    break
                if not cj.strip():
                    # Comment line: keep only if next non-comment line is still deeper than `indent`
                    k = j + 1
                    while k < n and raw_lines[k].strip() and not clean_lines[k].strip():
                        k += 1
                    if k < n and clean_lines[k].strip() and (len(raw_lines[k]) - len(raw_lines[k].lstrip(" "))) > indent:
                        chunk_raw.append(rj)
                        chunk_clean.append(cj)
                        end_ln = j + 1
                        j += 1
                        continue
                    break
                rj_indent = len(rj) - len(rj.lstrip(" "))
                if rj_indent > indent:
                    chunk_raw.append(rj)
                    chunk_clean.append(cj)
                    end_ln = j + 1
                    j += 1
                else:
                    break

        i = j
        slice_raw = "\n".join(chunk_raw).strip()
        slice_clean = "\n".join(chunk_clean).strip()
        first_clean, _ = _strip_leading_bullets(chunk_clean[0])
        head_tok = re.split(r"[\s(\[⟨;:,]+", first_clean)[0] if first_clean else "tactic"

        depth = max(0, (indent - base_indent) // 2 + bullet_count)

        before_state = GoalState(
            tag="main",
            hypotheses=[h.model_copy(update={"change": "unchanged"}) for h in current_hyps],
            target=current_target,
        )

        next_hyps = [h.model_copy(update={"change": "unchanged"}) for h in current_hyps]
        next_target = current_target

        have_match = re.match(r"have\s+([A-Za-z0-9_']+)\s*:\s*(.+?)\s*:=", first_clean)
        suffices_match = re.match(r"suffices\s+(?:([A-Za-z0-9_']+)\s*:\s*)?(.+?)\s+(?:by|from)\b", first_clean)
        let_match = re.match(r"(?:let|set)\s+([A-Za-z0-9_']+)\s*:=\s*(.+)", first_clean)
        intro_match = re.match(r"(?:intros?|rintro)(?:\s+([^;]+)|;|$)", first_clean)
        obtain_match = re.match(r"(?:obtain|rcases)\s+⟨([^⟩]+)⟩(?:\s*:\s*(.+?))?\s*:=\s*(.+)", first_clean)

        if have_match:
            next_hyps.append(Hypothesis(name=have_match.group(1), type=have_match.group(2).strip(), change="added"))
        elif suffices_match:
            nm = suffices_match.group(1) or "h_suff"
            next_hyps.append(Hypothesis(name=nm, type=suffices_match.group(2).strip(), change="added"))
        elif let_match:
            next_hyps.append(Hypothesis(name=let_match.group(1), type=f":= {let_match.group(2).strip()}", change="added"))
        elif intro_match and intro_match.group(1):
            for nm in re.findall(r"[A-Za-z_][A-Za-z0-9_']*", intro_match.group(1)):
                next_hyps.append(Hypothesis(name=nm, type="(introduced hypothesis)", change="added"))
        elif obtain_match:
            src_expr = obtain_match.group(2) or obtain_match.group(3)
            for nm in [x.strip() for x in obtain_match.group(1).split(",") if x.strip()]:
                next_hyps.append(Hypothesis(name=nm, type=f"(from {src_expr.strip()})", change="added"))
        elif head_tok == "by_contra":
            parts = first_clean.split()
            nm = parts[1] if len(parts) > 1 else "h"
            next_hyps.append(Hypothesis(name=nm, type=f"¬ ({current_target})", change="added"))
            next_target = "False"
        elif head_tok in ("exact", "exacts", "contradiction", "linarith", "nlinarith", "omega", "norm_num", "ring", "simp", "aesop", "grind", "sorry"):
            # Peek whether next non-empty line exits proof
            peek = i
            while peek < n and not clean_lines[peek].strip():
                peek += 1
            if peek >= n or (len(raw_lines[peek]) - len(raw_lines[peek].lstrip(" "))) == 0:
                next_target = "Goals accomplished"

        after_state = GoalState(tag="main", hypotheses=next_hyps, target=next_target)
        current_hyps = next_hyps
        current_target = next_target

        refs = sorted(set(re.findall(r"\b[A-Z][A-Za-z0-9_]*\.[A-Za-z0-9_.]+\b", slice_clean)))
        tokens = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", slice_clean))
        is_opaque = bool(tokens & OPAQUE_TACTICS)

        nodes.append(
            InfoTreeNode(
                node_id=next_id(),
                depth=depth,
                kind="tactic",
                tactic_kind=f"heuristic.{head_tok}",
                span=Span(start_line=start_ln, end_line=end_ln, start_col=1, end_col=80),
                source_slice=slice_raw,
                goals_before=[before_state],
                goals_after=[after_state],
                referenced_constants=refs,
                is_opaque_automation=is_opaque,
            )
        )

    return InfoTreeDocument(
        theorem_name=thm_name,
        statement_lean=stmt_lean,
        statement_latex=stmt_latex,
        source_code=source_code,
        lean_version="4.12.0 (heuristic)",
        extractor_mode="heuristic_parser",
        nodes=nodes,
    )


def extract_infotree(source_code: str) -> InfoTreeDocument:
    """
    Extract an InfoTreeDocument from Lean 4 source:
      1. If the source matches one of the bundled verified fixtures verbatim, return its precomputed InfoTree.
      2. Else if Lean 4 + Lake are available locally, run `infotree_dumper`.
      3. Otherwise fall back to the deterministic heuristic Lean 4 parser.
    """
    normalized = source_code.strip()
    for ex in get_curated_examples().values():
        if ex.infotree.source_code.strip() == normalized:
            return ex.infotree.model_copy(deep=True)

    live_doc = try_extract_via_lean4(source_code)
    if live_doc is not None:
        return live_doc

    return extract_infotree_heuristic(source_code)
