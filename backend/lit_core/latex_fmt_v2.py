# Purpose: Balanced-argument Lean 4 operator-to-LaTeX formatter (symbolic_literal_v0_2 variant).
from __future__ import annotations

import json
import re
from pathlib import Path

from .latex_fmt import validate_katex_safety

_CONFIG_PATH = Path(__file__).resolve().parent / "configs" / "symbolic_operators.json"


def _load_operator_config() -> dict:
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing symbolic operator config at {_CONFIG_PATH}")
    data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    required_keys = (
        "text_unicode_map",
        "math_unicode_map",
        "subscript_digit_map",
        "greek_ascii_allowlist",
        "simple_ident_map",
        "max_input_len",
        "max_output_len",
        "max_code_len",
    )
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required key '{key}' in {_CONFIG_PATH}")
    return data


_CFG = _load_operator_config()
TEXT_UNICODE_MAP: dict[str, str] = _CFG["text_unicode_map"]
MATH_UNICODE_MAP: dict[str, str] = _CFG["math_unicode_map"]
SUBSCRIPT_DIGIT_MAP: dict[str, str] = _CFG["subscript_digit_map"]
GREEK_ASCII_ALLOWLIST: dict[str, str] = _CFG["greek_ascii_allowlist"]
SIMPLE_IDENT_MAP: dict[str, str] = _CFG["simple_ident_map"]
DEFAULT_MAX_INPUT_LEN: int = int(_CFG["max_input_len"])
DEFAULT_MAX_OUTPUT_LEN: int = int(_CFG["max_output_len"])
DEFAULT_MAX_CODE_LEN: int = int(_CFG["max_code_len"])

_TEX_SPECIAL_RE = re.compile(r"([\\{}_^%$#&~])")
_TEX_SPECIAL_MAP: dict[str, str] = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "_": r"\_",
    "^": r"\^{}",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "&": r"\&",
    "~": r"\textasciitilde{}",
}

_EXPR_TOKEN_RE = re.compile(
    r"∀ᶠ|⌋₊|⌉₊|⁻¹|:=|=>|<;>|\|>|<\||<=|>=|!=|\+\+|\?\_|\*\*|"
    r"__LIT_SENTINEL_\d+__|"
    r"\d+(?:\.\d+)?|"
    r"[A-Za-z_][A-Za-z0-9_'.₀₁₂₃₄₅₆₇₈₉₊₋ᵥᶠ]*|"
    r"\S"
)

_ATOM_TERMINATORS = {
    ")",
    "]",
    "}",
    "⟩",
    "⌋",
    "⌉",
    "⌋₊",
    "⌉₊",
    ",",
    ";",
    "∧",
    "∨",
    "→",
    "←",
    "↔",
    "=",
    "≤",
    "≥",
    "<",
    ">",
    "≠",
    "∣",
    ":=",
    "=>",
    "<;>",
    "|>",
    "<|",
    "<=",
    ">=",
    "!=",
    "+",
    "-",
    "*",
    "/",
    "%",
    "^",
    "\\",
    ":",
    "in",
    "then",
    "else",
    "with",
    "using",
    "at",
    "by",
    "from",
}

_DOT_METHOD_SUFFIXES = ("card", "filter", "Nonempty", "Infinite", "Prime")
_NAMESPACE_PREFIXES = {"Finset", "Nat", "Set", "Int", "Real", "Filter", "List", "Max", "Min"}


def escape_latex_text_v2(s: str) -> str:
    """Escape text and identifiers for KaTeX \\text{...} / \\texttt{...} using externalized config."""
    if not s:
        return ""
    ascii_chars: list[str] = []
    for ch in s:
        if ch in TEXT_UNICODE_MAP:
            ascii_chars.append(TEXT_UNICODE_MAP[ch])
        elif ord(ch) > 127:
            ascii_chars.append("?")
        else:
            ascii_chars.append(ch)
    cleaned = "".join(ascii_chars)
    return _TEX_SPECIAL_RE.sub(lambda m: _TEX_SPECIAL_MAP[m.group(1)], cleaned)


def escape_latex_code_v2(s: str, max_len: int | None = None) -> str:
    """Collapse whitespace, truncate cleanly, and escape for KaTeX \\texttt{...}."""
    limit = max_len if max_len is not None else DEFAULT_MAX_CODE_LEN
    collapsed = re.sub(r"\s+", " ", s).strip()
    if limit > 3 and len(collapsed) > limit:
        cut = collapsed[: limit - 3].rsplit(" ", 1)[0]
        if len(cut) < limit // 2:
            cut = collapsed[: limit - 3]
        collapsed = cut + "..."
    return escape_latex_text_v2(collapsed)


def format_greek_or_ident(name: str) -> str:
    """Format a declaration or variable name, rendering allowlisted Greek ASCII symbols."""
    if name in GREEK_ASCII_ALLOWLIST:
        return GREEK_ASCII_ALLOWLIST[name]
    return rf"\mathrm{{{escape_latex_text_v2(name)}}}"


def _truncate_cleanly(expr: str, max_len: int) -> tuple[str, bool]:
    s = re.sub(r"\s+", " ", expr).strip().rstrip(";").strip()
    if len(s) <= max_len:
        return s, False
    cut = s[:max_len].rsplit(" ", 1)[0]
    if len(cut) < max_len // 2:
        cut = s[:max_len]
    return cut.strip(), True


def _strip_outer_parens(tokens: list[str]) -> list[str]:
    cur = tokens
    while len(cur) >= 2 and cur[0] == "(" and cur[-1] == ")":
        depth = 0
        wraps_all = True
        for idx, tok in enumerate(cur):
            if tok == "(":
                depth += 1
            elif tok == ")":
                depth -= 1
                if depth == 0 and idx < len(cur) - 1:
                    wraps_all = False
                    break
        if wraps_all and depth == 0:
            cur = cur[1:-1]
        else:
            break
    return cur


def _consume_balanced(
    tokens: list[str], start_idx: int, open_tok: str = "(", close_tok: str = ")"
) -> tuple[list[str], int, bool]:
    """Consume balanced delimiter group starting at start_idx. Returns (inner_tokens, next_idx, closed)."""
    depth = 0
    collected: list[str] = []
    idx = start_idx
    closed = False
    while idx < len(tokens):
        tok = tokens[idx]
        if tok == open_tok:
            depth += 1
            if depth > 1:
                collected.append(tok)
        elif tok == close_tok:
            depth -= 1
            if depth == 0:
                idx += 1
                closed = True
                break
            collected.append(tok)
        else:
            collected.append(tok)
        idx += 1
    return collected, idx, closed


def _consume_unparen_lambda(tokens: list[str], start_idx: int) -> tuple[list[str], int]:
    """Consume an unparenthesized `fun ... => ...` body up to top-level comma/semicolon/closer."""
    depth = 0
    idx = start_idx
    collected: list[str] = []
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in ("(", "[", "{", "⟨"):
            depth += 1
        elif tok in (")", "]", "}", "⟩"):
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and tok in (",", ";", "∧", "∨", "|>", "<|"):
            break
        collected.append(tok)
        idx += 1
    return collected, idx


def _consume_atom(tokens: list[str], pos: int) -> tuple[list[str] | None, int]:
    """Consume one balanced Lean application argument starting at `pos`."""
    n = len(tokens)
    if pos >= n:
        return None, pos
    tok = tokens[pos]
    if tok in _ATOM_TERMINATORS:
        return None, pos

    # Punctured/plain neighborhood expression `𝓝[>] a` or `𝓝 a`
    if tok == "𝓝":
        if pos + 3 < n and tokens[pos + 1] == "[" and tokens[pos + 3] == "]" and tokens[pos + 2] in (">", "<", "≥", "≤", ">=", "<="):
            arg, nxt = _consume_atom(tokens, pos + 4)
            if arg is not None:
                return tokens[pos : pos + 4] + arg, nxt
            return tokens[pos : pos + 4], pos + 4
        return ["𝓝"], pos + 1

    if tok == "(":
        inner, nxt, closed = _consume_balanced(tokens, pos, "(", ")")
        if not closed:
            return None, pos
        atom = ["("] + inner + [")"]
    elif tok == "[":
        inner, nxt, closed = _consume_balanced(tokens, pos, "[", "]")
        if not closed:
            return None, pos
        atom = ["["] + inner + ["]"]
    elif tok == "{":
        inner, nxt, closed = _consume_balanced(tokens, pos, "{", "}")
        if not closed:
            return None, pos
        atom = ["{"] + inner + ["}"]
    elif tok in ("⟨", "‹"):
        closer = "⟩" if tok == "⟨" else "›"
        inner, nxt, closed = _consume_balanced(tokens, pos, tok, closer)
        if not closed:
            return None, pos
        atom = [tok] + inner + [closer]
    elif tok == "fun":
        lam, nxt = _consume_unparen_lambda(tokens, pos)
        return lam, nxt
    else:
        atom = [tok]
        nxt = pos + 1

    # Attach chained postfix `.method` operations like `(Finset.Icc 1 k).filter P` or `(...).card`
    while nxt + 1 < n and tokens[nxt] == "." and tokens[nxt + 1] in _DOT_METHOD_SUFFIXES:
        method = tokens[nxt + 1]
        atom = atom + [".", method]
        nxt += 2
        if method == "filter":
            pred, after_pred = _consume_atom(tokens, nxt)
            if pred is not None:
                atom = atom + pred
                nxt = after_pred

    return atom, nxt


def _extract_lambda(atom_tokens: list[str], sentinels: dict[str, str]) -> tuple[str, list[str]] | None:
    """If `atom_tokens` is `(fun x [: T] => body)` or `fun x => body`, return (var_latex, body_tokens)."""
    toks = _strip_outer_parens(atom_tokens)
    if not toks or toks[0] != "fun":
        return None
    arrow_idx = -1
    depth = 0
    for idx in range(1, len(toks)):
        t = toks[idx]
        if t in ("(", "[", "{", "⟨"):
            depth += 1
        elif t in (")", "]", "}", "⟩") and depth > 0:
            depth -= 1
        elif t in ("=>", "↦") and depth == 0:
            arrow_idx = idx
            break
    if arrow_idx <= 1:
        return None

    binder_toks = toks[1:arrow_idx]
    # Strip optional `: Type` annotation in `fun M : ℕ => ...`
    var_toks: list[str] = []
    b_depth = 0
    for bt in binder_toks:
        if bt in ("(", "[", "{"):
            b_depth += 1
        elif bt in (")", "]", "}") and b_depth > 0:
            b_depth -= 1
        elif bt == ":" and b_depth == 0:
            break
        else:
            var_toks.append(bt)

    if not var_toks:
        var_toks = binder_toks[:1]
    var_tex = _render_tokens_v2(var_toks, sentinels).strip() or "x"
    body_toks = toks[arrow_idx + 1 :]
    return var_tex, body_toks


def _format_ident_v2(ident: str) -> tuple[str, bool, bool]:
    """Format an identifier token using config maps and Greek allowlist."""
    if ident in SIMPLE_IDENT_MAP:
        tex = SIMPLE_IDENT_MAP[ident]
        is_base = not tex.endswith(" ")
        return tex, False, is_base

    if set(ident) == {"_"}:
        return r"\cdot", False, True

    core = ident
    primes = ""
    sub_chars: list[str] = []
    while core and (core[-1] == "'" or core[-1] in SUBSCRIPT_DIGIT_MAP):
        ch = core[-1]
        core = core[:-1]
        if ch == "'":
            primes = "'" + primes
        else:
            sub_chars.append(SUBSCRIPT_DIGIT_MAP[ch])

    sub_str = "".join(reversed(sub_chars))
    if not core:
        return r"\cdot", False, True

    # Check exact Greek ASCII allowlist (excludes omega, excludes underscored h_theta)
    if core in GREEK_ASCII_ALLOWLIST:
        base_tex = GREEK_ASCII_ALLOWLIST[core]
    elif len(core) == 1 and core.isalpha():
        base_tex = core
    else:
        base_tex = rf"\mathrm{{{escape_latex_text_v2(core)}}}"

    if sub_str:
        base_tex = f"{base_tex}_{{{sub_str}}}"
    if primes:
        base_tex = f"{base_tex}{primes}"
    return base_tex, bool(primes), True


def _format_filter_expr(atom_tokens: list[str], sentinels: dict[str, str], *, unwrap_nhds: bool) -> str:
    """Format a Lean Filter expression (atTop, atBot, nhds L, 𝓝[>] a, Filter.map g F)."""
    toks = _strip_outer_parens(atom_tokens)
    if not toks:
        return r"\cdot"

    if toks == ["Filter.atTop"]:
        return r"+\infty"
    if toks == ["Filter.atBot"]:
        return r"-\infty"

    if toks[0] == "nhds":
        if len(toks) > 1:
            arg_tex = _render_tokens_v2(_strip_outer_parens(toks[1:]), sentinels)
            return arg_tex if unwrap_nhds else rf"\mathcal{{N}}({arg_tex})"
        return r"\mathcal{N}"

    if toks[0] == "𝓝":
        if len(toks) >= 4 and toks[1] == "[" and toks[3] == "]" and toks[2] in (">", "<", "≥", "≤", ">=", "<="):
            op_map = {">": ">", "<": "<", "≥": r"\ge", "≤": r"\le", ">=": r"\ge", "<=": r"\le"}
            sup_map = {">": "+", "<": "-", "≥": r"\ge", "≤": r"\le", ">=": r"\ge", "<=": r"\le"}
            rest = _strip_outer_parens(toks[4:])
            arg_tex = _render_tokens_v2(rest, sentinels) if rest else r"\cdot"
            if unwrap_nhds:
                return f"{arg_tex}^{{{sup_map[toks[2]]}}}"
            return rf"\mathcal{{N}}_{{{op_map[toks[2]]}}}({arg_tex})"
        if len(toks) > 1:
            arg_tex = _render_tokens_v2(_strip_outer_parens(toks[1:]), sentinels)
            return arg_tex if unwrap_nhds else rf"\mathcal{{N}}({arg_tex})"
        return r"\mathcal{N}"

    return _render_tokens_v2(toks, sentinels)


def _apply_postfix_method(prev_tex: str, method: str, pred_toks: list[str] | None, sentinels: dict[str, str]) -> str:
    if method == "card":
        return f"|{prev_tex}|"
    if method == "Nonempty":
        return rf"{prev_tex} \neq \emptyset"
    if method == "Infinite":
        return rf"|{prev_tex}| = \infty"
    if method == "Prime":
        return rf"{prev_tex} \text{{ prime}}"
    if method == "filter":
        if pred_toks is None:
            return rf"\mathrm{{filter}}({prev_tex})"
        lam = _extract_lambda(pred_toks, sentinels)
        if lam is not None:
            var_tex, body_toks = lam
            body_tex = _render_tokens_v2(body_toks, sentinels)
            return rf"\{{ {var_tex} \in {prev_tex} \mid {body_tex} \}}"
        if _strip_outer_parens(pred_toks) == ["Nat.Prime"]:
            return rf"\{{ p \in {prev_tex} \mid p \text{{ prime}} \}}"
        pred_tex = _render_tokens_v2(_strip_outer_parens(pred_toks), sentinels)
        return rf"\{{ x \in {prev_tex} \mid {pred_tex}(x) \}}"
    return prev_tex


def _is_simple_single_atom(atom_tokens: list[str]) -> bool:
    stripped = _strip_outer_parens(atom_tokens)
    return len(stripped) == 1 and (stripped[0].isalnum() or stripped[0].replace("_", "").isalnum())


def _render_tokens_v2(tokens: list[str], sentinels: dict[str, str]) -> str:
    out: list[str] = []
    last_has_sup = False
    can_be_base = False

    def emit(tex: str, *, has_sup: bool = False, is_base: bool = False) -> None:
        nonlocal last_has_sup, can_be_base
        out.append(tex)
        last_has_sup = has_sup
        can_be_base = is_base

    def render_arg(atom_toks: list[str]) -> str:
        return _render_tokens_v2(_strip_outer_parens(atom_toks), sentinels)

    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]

        if tok in sentinels:
            emit(sentinels[tok], has_sup=False, is_base=True)
            i += 1
            continue

        # Balanced parentheses rendered as a single unit so postfix .card / .filter / ^ bind to whole group
        if tok == "(":
            inner, nxt_i, closed = _consume_balanced(tokens, i, "(", ")")
            if not closed:
                emit("(", has_sup=False, is_base=False)
                i += 1
                continue
            inner_tex = _render_tokens_v2(inner, sentinels)
            # Strip redundant parens if attached immediately to postfix .method, otherwise keep (...)
            if nxt_i + 1 < n and tokens[nxt_i] == "." and tokens[nxt_i + 1] in _DOT_METHOD_SUFFIXES:
                emit(inner_tex, has_sup=False, is_base=True)
            else:
                emit(f"({inner_tex})", has_sup=False, is_base=True)
            i = nxt_i
            continue

        # Postfix dot-method following a rendered expression (e.g. `(Finset.Icc 1 k).filter P` or `(...).card`)
        if tok == "." and out and can_be_base and i + 1 < n and tokens[i + 1] in _DOT_METHOD_SUFFIXES:
            method = tokens[i + 1]
            i += 2
            pred_toks: list[str] | None = None
            if method == "filter":
                pred_toks, i = _consume_atom(tokens, i)
            out[-1] = _apply_postfix_method(out[-1], method, pred_toks, sentinels)
            last_has_sup = False
            can_be_base = True
            continue

        # --- Structured Prefix Operators (27 audited classes) ---
        if tok == "Filter.Tendsto":
            f_toks, p1 = _consume_atom(tokens, i + 1)
            src_toks, p2 = _consume_atom(tokens, p1) if f_toks is not None else (None, p1)
            dst_toks, p3 = _consume_atom(tokens, p2) if src_toks is not None else (None, p2)
            if f_toks is not None and src_toks is not None and dst_toks is not None:
                src_tex = _format_filter_expr(src_toks, sentinels, unwrap_nhds=False)
                dst_tex = _format_filter_expr(dst_toks, sentinels, unwrap_nhds=True)
                lam = _extract_lambda(f_toks, sentinels)
                if lam is not None:
                    var_tex, body_toks = lam
                    body_tex = _render_tokens_v2(body_toks, sentinels)
                    emit(rf"\lim_{{{var_tex} \to {src_tex}}} {body_tex} = {dst_tex}", has_sup=False, is_base=False)
                else:
                    f_tex = render_arg(f_toks)
                    emit(rf"{f_tex} \xrightarrow{{{src_tex}}} {dst_tex}", has_sup=False, is_base=False)
                i = p3
            else:
                emit(r"\lim", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Filter.map":
            g_toks, p1 = _consume_atom(tokens, i + 1)
            f_toks, p2 = _consume_atom(tokens, p1) if g_toks is not None else (None, p1)
            if g_toks is not None and f_toks is not None:
                lam = _extract_lambda(g_toks, sentinels)
                if lam is not None:
                    var_tex, body_toks = lam
                    g_tex = rf"{var_tex} \mapsto {_render_tokens_v2(body_toks, sentinels)}"
                else:
                    g_tex = render_arg(g_toks)
                f_tex = _format_filter_expr(f_toks, sentinels, unwrap_nhds=False)
                emit(rf"({g_tex})_{{*}}({f_tex})", has_sup=False, is_base=True)
                i = p2
            else:
                emit(r"\mathrm{map}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "𝓝":
            if i + 3 < n and tokens[i + 1] == "[" and tokens[i + 3] == "]" and tokens[i + 2] in (">", "<", "≥", "≤", ">=", "<="):
                op_map = {">": ">", "<": "<", "≥": r"\ge", "≤": r"\le", ">=": r"\ge", "<=": r"\le"}
                op_sym = op_map[tokens[i + 2]]
                arg_toks, nxt = _consume_atom(tokens, i + 4)
                if arg_toks is not None:
                    emit(rf"\mathcal{{N}}_{{{op_sym}}}({render_arg(arg_toks)})", has_sup=False, is_base=True)
                    i = nxt
                else:
                    emit(rf"\mathcal{{N}}_{{{op_sym}}}", has_sup=False, is_base=True)
                    i += 4
                continue
            arg_toks, nxt = _consume_atom(tokens, i + 1)
            if arg_toks is not None:
                emit(rf"\mathcal{{N}}({render_arg(arg_toks)})", has_sup=False, is_base=True)
                i = nxt
            else:
                emit(r"\mathcal{N}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "nhds":
            arg_toks, nxt = _consume_atom(tokens, i + 1)
            if arg_toks is not None:
                emit(rf"\mathcal{{N}}({render_arg(arg_toks)})", has_sup=False, is_base=True)
                i = nxt
            else:
                emit(r"\mathcal{N}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Nat.choose":
            a1, p1 = _consume_atom(tokens, i + 1)
            a2, p2 = _consume_atom(tokens, p1) if a1 is not None else (None, p1)
            if a1 is not None and a2 is not None:
                emit(rf"\binom{{{render_arg(a1)}}}{{{render_arg(a2)}}}", has_sup=False, is_base=True)
                i = p2
            else:
                emit(r"\binom{\cdot}{\cdot}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Nat.factorial":
            a1, p1 = _consume_atom(tokens, i + 1)
            if a1 is not None:
                arg_tex = render_arg(a1)
                if _is_simple_single_atom(a1):
                    emit(f"{arg_tex}!", has_sup=False, is_base=True)
                else:
                    emit(f"({arg_tex})!", has_sup=False, is_base=True)
                i = p1
            else:
                emit("!", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Nat.descFactorial":
            a1, p1 = _consume_atom(tokens, i + 1)
            a2, p2 = _consume_atom(tokens, p1) if a1 is not None else (None, p1)
            if a1 is not None and a2 is not None:
                emit(rf"({render_arg(a1)})_{{{render_arg(a2)}}}", has_sup=False, is_base=True)
                i = p2
            else:
                emit(r"(\cdot)_{(\cdot)}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "padicValNat":
            a1, p1 = _consume_atom(tokens, i + 1)
            a2, p2 = _consume_atom(tokens, p1) if a1 is not None else (None, p1)
            if a1 is not None and a2 is not None:
                emit(rf"v_{{{render_arg(a1)}}}({render_arg(a2)})", has_sup=False, is_base=True)
                i = p2
            else:
                emit(r"v_{p}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Nat.factorization":
            n_toks, p1 = _consume_atom(tokens, i + 1)
            p_toks, p2 = _consume_atom(tokens, p1) if n_toks is not None else (None, p1)
            if n_toks is not None and p_toks is not None:
                emit(rf"v_{{{render_arg(p_toks)}}}({render_arg(n_toks)})", has_sup=False, is_base=True)
                i = p2
            elif n_toks is not None:
                emit(rf"v({render_arg(n_toks)})", has_sup=False, is_base=True)
                i = p1
            else:
                emit(r"v", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Nat.log":
            a1, p1 = _consume_atom(tokens, i + 1)
            a2, p2 = _consume_atom(tokens, p1) if a1 is not None else (None, p1)
            if a1 is not None and a2 is not None:
                emit(rf"\lfloor \log_{{{render_arg(a1)}}}({render_arg(a2)}) \rfloor", has_sup=False, is_base=True)
                i = p2
            else:
                emit(r"\lfloor \log \rfloor", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Nat.floor":
            a1, p1 = _consume_atom(tokens, i + 1)
            if a1 is not None:
                emit(rf"\lfloor {render_arg(a1)} \rfloor", has_sup=False, is_base=True)
                i = p1
            else:
                emit(r"\lfloor \cdot \rfloor", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Nat.ceil":
            a1, p1 = _consume_atom(tokens, i + 1)
            if a1 is not None:
                emit(rf"\lceil {render_arg(a1)} \rceil", has_sup=False, is_base=True)
                i = p1
            else:
                emit(r"\lceil \cdot \rceil", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Int.natAbs":
            a1, p1 = _consume_atom(tokens, i + 1)
            if a1 is not None:
                emit(rf"|{render_arg(a1)}|", has_sup=False, is_base=True)
                i = p1
            else:
                emit(r"|\cdot|", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Max.max":
            a1, p1 = _consume_atom(tokens, i + 1)
            a2, p2 = _consume_atom(tokens, p1) if a1 is not None else (None, p1)
            if a1 is not None and a2 is not None:
                emit(rf"\max({render_arg(a1)}, {render_arg(a2)})", has_sup=False, is_base=True)
                i = p2
            else:
                emit(r"\max", has_sup=False, is_base=True)
                i += 1
            continue

        if tok in ("Finset.Icc", "Finset.Ico", "Finset.Ioo", "Finset.Ioc"):
            a1, p1 = _consume_atom(tokens, i + 1)
            a2, p2 = _consume_atom(tokens, p1) if a1 is not None else (None, p1)
            lb = "[" if tok in ("Finset.Icc", "Finset.Ico") else "("
            rb = "]" if tok in ("Finset.Icc", "Finset.Ioc") else ")"
            if a1 is not None and a2 is not None:
                emit(rf"{lb}{render_arg(a1)}, {render_arg(a2)}{rb}", has_sup=False, is_base=True)
                i = p2
            else:
                emit(rf"{lb}\cdot, \cdot{rb}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Finset.range":
            a1, p1 = _consume_atom(tokens, i + 1)
            if a1 is not None:
                emit(rf"\{{0, \dots, {render_arg(a1)} - 1\}}", has_sup=False, is_base=True)
                i = p1
            else:
                emit(r"\{0, \dots\}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Finset.filter":
            p_toks, p1 = _consume_atom(tokens, i + 1)
            s_toks, p2 = _consume_atom(tokens, p1) if p_toks is not None else (None, p1)
            if p_toks is not None and s_toks is not None:
                s_tex = render_arg(s_toks)
                emit(_apply_postfix_method(s_tex, "filter", p_toks, sentinels), has_sup=False, is_base=True)
                i = p2
            else:
                emit(r"\mathrm{filter}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Finset.card":
            a1, p1 = _consume_atom(tokens, i + 1)
            if a1 is not None:
                emit(rf"|{render_arg(a1)}|", has_sup=False, is_base=True)
                i = p1
            else:
                emit(r"|\cdot|", has_sup=False, is_base=True)
                i += 1
            continue

        if tok in ("Finset.sup", "Finset.biUnion"):
            op_sym = r"\sup" if tok == "Finset.sup" else r"\bigcup"
            s_toks, p1 = _consume_atom(tokens, i + 1)
            f_toks, p2 = _consume_atom(tokens, p1) if s_toks is not None else (None, p1)
            if s_toks is not None and f_toks is not None:
                s_tex = render_arg(s_toks)
                lam = _extract_lambda(f_toks, sentinels)
                if lam is not None:
                    var_tex, body_toks = lam
                    body_tex = _render_tokens_v2(body_toks, sentinels)
                    emit(rf"{op_sym}_{{{var_tex} \in {s_tex}}} {body_tex}", has_sup=False, is_base=True)
                else:
                    emit(rf"{op_sym}_{{{s_tex}}} {render_arg(f_toks)}", has_sup=False, is_base=True)
                i = p2
            else:
                emit(op_sym, has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Finset.image":
            f_toks, p1 = _consume_atom(tokens, i + 1)
            s_toks, p2 = _consume_atom(tokens, p1) if f_toks is not None else (None, p1)
            if f_toks is not None and s_toks is not None:
                s_tex = render_arg(s_toks)
                lam = _extract_lambda(f_toks, sentinels)
                if lam is not None:
                    var_tex, body_toks = lam
                    body_tex = _render_tokens_v2(body_toks, sentinels)
                    emit(rf"\{{ {body_tex} \mid {var_tex} \in {s_tex} \}}", has_sup=False, is_base=True)
                else:
                    emit(rf"{render_arg(f_toks)}({s_tex})", has_sup=False, is_base=True)
                i = p2
            else:
                emit(r"\mathrm{image}", has_sup=False, is_base=True)
                i += 1
            continue

        if tok == "Set.Infinite":
            a1, p1 = _consume_atom(tokens, i + 1)
            if a1 is not None:
                emit(rf"|{render_arg(a1)}| = \infty", has_sup=False, is_base=False)
                i = p1
            else:
                emit(r"|\cdot| = \infty", has_sup=False, is_base=False)
                i += 1
            continue

        if tok == "Nat.Prime":
            a1, p1 = _consume_atom(tokens, i + 1)
            if a1 is not None:
                emit(rf"{render_arg(a1)} \text{{ prime}}", has_sup=False, is_base=False)
                i = p1
            else:
                emit(r"\text{prime}", has_sup=False, is_base=False)
                i += 1
            continue

        # Dotted postfix methods on identifiers, e.g. `A.card`, `S.Infinite`, `S.Nonempty`, `p.Prime`
        if "." in tok:
            prefix, suffix = tok.rsplit(".", 1)
            if suffix in ("card", "Nonempty", "Infinite", "Prime") and prefix not in _NAMESPACE_PREFIXES:
                prefix_tex = _render_tokens_v2([prefix], sentinels)
                emit(_apply_postfix_method(prefix_tex, suffix, None, sentinels), has_sup=False, is_base=suffix == "card")
                i += 1
                continue

        # Exponent / superscript handling (identical KaTeX-safe guard as v0.1)
        if tok == "^":
            if not out or not can_be_base:
                base_prefix = r"{\cdot}"
                if i + 1 >= n:
                    emit(r"\^{}", has_sup=False, is_base=True)
                    i += 1
                    continue
            else:
                base_prefix = ""
                if last_has_sup:
                    out[-1] = "{" + out[-1] + "}"

            if i + 1 >= n:
                emit(r"\text{\^{}}", has_sup=False, is_base=False)
                i += 1
                continue

            nxt = tokens[i + 1]
            if nxt == "(":
                inner_toks, next_i, _ = _consume_balanced(tokens, i + 1, "(", ")")
                exp_tex = _render_tokens_v2(inner_toks, sentinels) if inner_toks else r"\cdot"
                i = next_i
            elif nxt == "-" and i + 2 < n:
                if tokens[i + 2] == "(":
                    inner_toks, next_i, _ = _consume_balanced(tokens, i + 2, "(", ")")
                    exp_tex = "-" + (_render_tokens_v2(inner_toks, sentinels) if inner_toks else r"\cdot")
                    i = next_i
                else:
                    atom_tex = _render_tokens_v2([tokens[i + 2]], sentinels)
                    exp_tex = f"-{atom_tex}"
                    i += 3
            elif nxt in (")", "]", "}", "⟩", ",", ";", "="):
                emit(r"\text{\^{}}", has_sup=False, is_base=False)
                i += 1
                continue
            else:
                exp_tex = _render_tokens_v2([nxt], sentinels)
                i += 2

            if base_prefix:
                emit(f"{base_prefix}^{{{exp_tex}}}", has_sup=True, is_base=True)
            else:
                out[-1] = f"{out[-1]}^{{{exp_tex}}}"
                last_has_sup = True
                can_be_base = True
            continue

        # Multi-character Lean symbols & operators
        if tok == "∀ᶠ":
            emit(r"\forall^{\mathrm{ev}} ", has_sup=False, is_base=False)
        elif tok == "⌋₊":
            emit(r"\rfloor_{+}", has_sup=False, is_base=True)
        elif tok == "⌉₊":
            emit(r"\rceil_{+}", has_sup=False, is_base=True)
        elif tok == "⁻¹":
            if out and can_be_base:
                if last_has_sup:
                    out[-1] = "{" + out[-1] + "}"
                out[-1] = f"{out[-1]}^{{-1}}"
                last_has_sup = True
                can_be_base = True
            else:
                emit(r"(\cdot)^{-1}", has_sup=True, is_base=True)
        elif tok in ("²", "³"):
            pow_dig = "2" if tok == "²" else "3"
            if out and can_be_base:
                if last_has_sup:
                    out[-1] = "{" + out[-1] + "}"
                out[-1] = f"{out[-1]}^{{{pow_dig}}}"
                last_has_sup = True
                can_be_base = True
            else:
                emit(rf"(\cdot)^{{{pow_dig}}}", has_sup=True, is_base=True)
        elif tok == "|>":
            emit(r"\triangleright ", has_sup=False, is_base=False)
        elif tok == "<|":
            emit(r"\triangleleft ", has_sup=False, is_base=False)
        elif tok == "=>":
            emit(r"\mapsto ", has_sup=False, is_base=False)
        elif tok == ":=":
            emit(":=", has_sup=False, is_base=False)
        elif tok == "<;>":
            emit(";", has_sup=False, is_base=False)
        elif tok == "<=":
            emit(r"\le ", has_sup=False, is_base=False)
        elif tok == ">=":
            emit(r"\ge ", has_sup=False, is_base=False)
        elif tok == "!=":
            emit(r"\neq ", has_sup=False, is_base=False)
        elif tok == "++":
            emit(r"\mathbin{+\!\!+}", has_sup=False, is_base=False)
        elif tok == "?_":
            emit("?", has_sup=False, is_base=True)
        elif tok == "**":
            emit(r"\cdot ", has_sup=False, is_base=False)
        elif tok == "{":
            emit(r"\{", has_sup=False, is_base=False)
        elif tok == "}":
            emit(r"\}", has_sup=False, is_base=True)
        elif tok == "%":
            emit(r"\bmod ", has_sup=False, is_base=False)
        elif tok == "\\":
            emit(r"\setminus ", has_sup=False, is_base=False)
        elif tok == "$":
            emit(r"\$", has_sup=False, is_base=True)
        elif tok == "#":
            emit(r"\#", has_sup=False, is_base=True)
        elif tok == "&":
            emit(r"\&", has_sup=False, is_base=False)
        elif tok == "~":
            emit(r"\sim ", has_sup=False, is_base=False)
        elif tok == "'":
            emit(r"\text{'}", has_sup=False, is_base=True)
        elif tok == "_":
            emit(r"\cdot", has_sup=False, is_base=True)
        elif tok in MATH_UNICODE_MAP:
            tex = MATH_UNICODE_MAP[tok]
            is_closing = tok in ("⌋", "⌉", "⟩", "›", "∅", "ℕ", "ℤ", "ℚ", "ℝ", "ℂ", "∞", "𝓝")
            is_greek = tok in ("ε", "δ", "μ", "π", "α", "β", "γ", "θ", "λ", "σ", "τ", "φ", "ψ", "ω")
            emit(tex, has_sup=False, is_base=is_closing or is_greek)
        elif tok[0].isdigit():
            emit(tok, has_sup=False, is_base=True)
        elif tok[0].isalpha() or tok[0] == "_":
            frag, has_sup, is_base = _format_ident_v2(tok)
            emit(frag, has_sup=has_sup, is_base=is_base)
        elif ord(tok[0]) > 127:
            emit(r"\text{" + escape_latex_text_v2(tok) + "}", has_sup=False, is_base=True)
        else:
            emit(tok, has_sup=False, is_base=tok in (")", "]", "!"))

        i += 1

    return " ".join(out)


def lean_expr_to_latex_v2(expr: str, max_len: int | None = None) -> str:
    """
    Balanced-argument Lean 4 expression formatter (`symbolic_literal_v0_2`).
    Rewrites multi-argument Mathlib operators, filter limits, punctured neighborhoods,
    dot-methods, and config-allowlisted Greek symbols into KaTeX-safe LaTeX.
    """
    if not expr or not expr.strip():
        return r"\cdot"

    in_limit = max_len if max_len is not None else DEFAULT_MAX_INPUT_LEN
    truncated_raw, was_truncated = _truncate_cleanly(expr, in_limit)
    sentinels: dict[str, str] = {}
    counter = 0

    def next_sentinel(tex: str) -> str:
        nonlocal counter
        key = f"__LIT_SENTINEL_{counter}__"
        counter += 1
        sentinels[key] = tex
        return f" {key} "

    s = re.sub(
        r"=o\[Filter\.atTop\]",
        lambda _: next_sentinel(r"= o_{\infty}"),
        truncated_raw,
    )
    s = re.sub(
        r"=o\[([^\]]+)\]",
        lambda m: next_sentinel(rf"= o_{{{lean_expr_to_latex_v2(m.group(1), max_len=80)}}}"),
        s,
    )
    s = re.sub(
        r"\[(?:Z|P)?MOD\s+([^\]]+)\]",
        lambda m: next_sentinel(rf"\pmod{{{lean_expr_to_latex_v2(m.group(1), max_len=80)}}}"),
        s,
    )

    tokens = _EXPR_TOKEN_RE.findall(s)
    rendered = _render_tokens_v2(tokens, sentinels)
    rendered = re.sub(r"\s+", " ", rendered).strip()
    rendered = re.sub(r"\(\s+", "(", rendered)
    rendered = re.sub(r"\s+\)", ")", rendered)
    rendered = re.sub(r"\s+,", ",", rendered)
    rendered = re.sub(r"\s+:", ":", rendered)

    if was_truncated:
        rendered = f"{rendered}\\; \\ldots"

    if not rendered or validate_katex_safety(rendered):
        return rf"\texttt{{{escape_latex_code_v2(expr, max_len=DEFAULT_MAX_CODE_LEN)}}}"

    return rendered
