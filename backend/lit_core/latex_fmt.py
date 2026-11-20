"""Deterministic Lean 4 comment stripping, KaTeX-safe escaping, and math expression formatting."""
from __future__ import annotations

import re

# Unicode -> ASCII replacements for KaTeX \text{...} / \texttt{...} modes
_TEXT_UNICODE_MAP: dict[str, str] = {
    "ℕ": "N",
    "ℤ": "Z",
    "ℚ": "Q",
    "ℝ": "R",
    "ℂ": "C",
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "₊": "+",
    "₋": "-",
    "⁻": "^-",
    "¹": "1",
    "²": "2",
    "³": "3",
    "ᶠ": "f",
    "ᵥ": "v",
    "≤": "<=",
    "≥": ">=",
    "≠": "!=",
    "∣": "|",
    "∧": "/\\",
    "∨": "\\/",
    "¬": "not ",
    "→": "->",
    "←": "<-",
    "↔": "<->",
    "↦": "|->",
    "∈": " in ",
    "∉": " not in ",
    "⊆": " subseteq ",
    "⊂": " subset ",
    "∪": " U ",
    "∩": " cap ",
    "∅": "{}",
    "∀": "forall ",
    "∃": "exists ",
    "∑": "sum ",
    "∏": "prod ",
    "⟨": "<",
    "⟩": ">",
    "‹": "<",
    "›": ">",
    "⌊": "floor(",
    "⌋": ")",
    "⌈": "ceil(",
    "⌉": ")",
    "·": ".",
    "•": "*",
    "∘": "o",
    "≡": "===",
    "⊢": "|-",
    "↑": "^",
    "▸": ">",
    "ε": "eps",
    "δ": "delta",
    "μ": "mu",
    "π": "pi",
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "θ": "theta",
    "λ": "lambda",
    "σ": "sigma",
    "τ": "tau",
    "φ": "phi",
    "ψ": "psi",
    "ω": "omega",
    "∞": "inf",
    "—": "-",
    "–": "-",
    "…": "...",
    "“": '"',
    "”": '"',
    "’": "'",
}

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

# Unicode -> KaTeX math mode replacements
_MATH_UNICODE_MAP: dict[str, str] = {
    "∀": r"\forall ",
    "∃": r"\exists ",
    "ℕ": r"\mathbb{N}",
    "ℤ": r"\mathbb{Z}",
    "ℚ": r"\mathbb{Q}",
    "ℝ": r"\mathbb{R}",
    "ℂ": r"\mathbb{C}",
    "≤": r"\le ",
    "≥": r"\ge ",
    "≠": r"\neq ",
    "∣": r"\mid ",
    "∧": r"\land ",
    "∨": r"\lor ",
    "¬": r"\neg ",
    "→": r"\to ",
    "←": r"\leftarrow ",
    "↔": r"\iff ",
    "↦": r"\mapsto ",
    "∈": r"\in ",
    "∉": r"\notin ",
    "⊆": r"\subseteq ",
    "⊂": r"\subset ",
    "∪": r"\cup ",
    "∩": r"\cap ",
    "∅": r"\emptyset ",
    "∑": r"\sum ",
    "∏": r"\prod ",
    "·": r"\cdot ",
    "•": r"\cdot ",
    "∘": r"\circ ",
    "≡": r"\equiv ",
    "⊢": r"\vdash ",
    "↑": r"\uparrow ",
    "▸": r"\triangleright ",
    "⌊": r"\lfloor ",
    "⌋": r"\rfloor ",
    "⌈": r"\lceil ",
    "⌉": r"\rceil ",
    "⟨": r"\langle ",
    "⟩": r"\rangle ",
    "‹": r"\langle ",
    "›": r"\rangle ",
    "ε": r"\varepsilon ",
    "δ": r"\delta ",
    "μ": r"\mu ",
    "π": r"\pi ",
    "α": r"\alpha ",
    "β": r"\beta ",
    "γ": r"\gamma ",
    "θ": r"\theta ",
    "λ": r"\lambda ",
    "σ": r"\sigma ",
    "τ": r"\tau ",
    "φ": r"\varphi ",
    "ψ": r"\psi ",
    "ω": r"\omega ",
    "∞": r"\infty ",
}

_KNOWN_MATH_IDENTS: dict[str, str] = {
    "Real.log": r"\log",
    "Nat.log": r"\log",
    "Real.exp": r"\exp",
    "Real.sqrt": r"\mathrm{sqrt}",
    "Nat.gcd": r"\gcd",
    "Nat.Prime": r"\mathrm{Prime}",
    "Nat.Coprime": r"\mathrm{Coprime}",
    "Nat.choose": r"\mathrm{choose}",
    "Nat.factorial": r"\mathrm{fact}",
    "padicValNat": r"v",
    "Filter.atTop": r"+\infty",
    "Filter.Tendsto": r"\mathrm{Tendsto}",
    "nhds": r"\mathcal{N}",
    "Finset.card": r"\mathrm{card}",
    "Finset.Icc": r"\mathrm{Icc}",
    "Finset.Ico": r"\mathrm{Ico}",
    "Finset.Iio": r"\mathrm{Iio}",
    "Finset.range": r"\mathrm{range}",
    "Finset.filter": r"\mathrm{filter}",
    "Finset.univ": r"\mathrm{univ}",
    "Nat.digits": r"\mathrm{digits}",
    "Nat.ofDigits": r"\mathrm{ofDigits}",
    "Nat.floor": r"\mathrm{floor}",
    "Nat.ceil": r"\mathrm{ceil}",
    "List.length": r"\mathrm{length}",
    "List.take": r"\mathrm{take}",
    "fun": r"\lambda ",
    "if": r"\text{if }",
    "then": r"\text{ then }",
    "else": r"\text{ else }",
    "let": r"\text{let }",
    "in": r"\text{ in }",
    "by": r"\text{by }",
    "show": r"\text{show }",
    "from": r"\text{ from }",
}

_SUBSCRIPT_DIGIT_MAP: dict[str, str] = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "₊": "+",
    "₋": "-",
    "ᵥ": "v",
    "ᶠ": "f",
}

_EXPR_TOKEN_RE = re.compile(
    r"∀ᶠ|⌋₊|⌉₊|⁻¹|:=|=>|<;>|\|>|<\||<=|>=|!=|\+\+|\?\_|\*\*|"
    r"__LIT_SENTINEL_\d+__|"
    r"\d+(?:\.\d+)?|"
    r"[A-Za-z_][A-Za-z0-9_'.₀₁₂₃₄₅₆₇₈₉₊₋ᵥᶠ]*|"
    r"\S"
)


def strip_lean_comments_preserving_lines(source_code: str) -> str:
    """
    Strip Lean 4 `--` line comments and nested `/- ... -/` block comments
    while preserving exact newline count and line numbering.
    """
    out: list[str] = []
    depth = 0
    in_str = False
    i = 0
    n = len(source_code)

    while i < n:
        ch = source_code[i]
        nxt = source_code[i + 1] if i + 1 < n else ""

        if depth == 0:
            if ch == '"':
                # Track escaped quotes inside string literals
                backslashes = 0
                k = i - 1
                while k >= 0 and source_code[k] == "\\":
                    backslashes += 1
                    k -= 1
                if backslashes % 2 == 0:
                    in_str = not in_str
                out.append(ch)
                i += 1
                continue

            if not in_str:
                if ch == "/" and nxt == "-":
                    depth += 1
                    out.append("  ")
                    i += 2
                    continue
                if ch == "-" and nxt == "-":
                    while i < n and source_code[i] != "\n":
                        out.append(" ")
                        i += 1
                    continue

            out.append(ch)
            i += 1
        else:
            if ch == "/" and nxt == "-":
                depth += 1
                out.append("  ")
                i += 2
            elif ch == "-" and nxt == "/":
                depth -= 1
                out.append("  ")
                i += 2
            elif ch == "\n":
                out.append("\n")
                i += 1
            else:
                out.append(" ")
                i += 1

    return "".join(out)


def escape_latex_text(s: str) -> str:
    """Escape arbitrary text/identifiers for safe rendering inside KaTeX \\text{...} / \\texttt{...}."""
    if not s:
        return ""
    ascii_chars: list[str] = []
    for ch in s:
        if ch in _TEXT_UNICODE_MAP:
            ascii_chars.append(_TEXT_UNICODE_MAP[ch])
        elif ord(ch) > 127:
            ascii_chars.append("?")
        else:
            ascii_chars.append(ch)
    cleaned = "".join(ascii_chars)
    return _TEX_SPECIAL_RE.sub(lambda m: _TEX_SPECIAL_MAP[m.group(1)], cleaned)


def escape_latex_code(s: str, max_len: int = 160) -> str:
    """Collapse whitespace, truncate cleanly, and escape for KaTeX \\texttt{...}."""
    collapsed = re.sub(r"\s+", " ", s).strip()
    if max_len > 3 and len(collapsed) > max_len:
        cut = collapsed[: max_len - 3].rsplit(" ", 1)[0]
        if len(cut) < max_len // 2:
            cut = collapsed[: max_len - 3]
        collapsed = cut + "..."
    return escape_latex_text(collapsed)


def _format_ident(ident: str) -> tuple[str, bool, bool]:
    """
    Format a Lean identifier token for KaTeX math mode.
    Returns (latex_fragment, has_superscript, is_valid_base).
    """
    if ident in _KNOWN_MATH_IDENTS:
        tex = _KNOWN_MATH_IDENTS[ident]
        is_base = not tex.endswith(" ")
        return tex, False, is_base

    # Standalone `_` wildcard
    if set(ident) == {"_"}:
        return r"\cdot", False, True

    # Separate trailing Unicode subscript chars and primes
    core = ident
    primes = ""
    sub_chars: list[str] = []

    while core and (core[-1] == "'" or core[-1] in _SUBSCRIPT_DIGIT_MAP):
        ch = core[-1]
        core = core[:-1]
        if ch == "'":
            primes = "'" + primes
        else:
            sub_chars.append(_SUBSCRIPT_DIGIT_MAP[ch])

    sub_str = "".join(reversed(sub_chars))

    # Strip trailing `_` if identifier ended with `_` before subscripts/primes
    if not core:
        return r"\cdot", False, True

    # Single-letter ASCII variable renders cleanly in math italic
    if len(core) == 1 and core.isalpha():
        base_tex = core
    else:
        # Multi-character or underscored identifier inside \mathrm{...} with escaped underscores
        safe_core = escape_latex_text(core)
        base_tex = rf"\mathrm{{{safe_core}}}"

    if sub_str:
        base_tex = f"{base_tex}_{{{sub_str}}}"
    if primes:
        base_tex = f"{base_tex}{primes}"

    return base_tex, bool(primes), True


def _truncate_cleanly(expr: str, max_len: int) -> tuple[str, bool]:
    s = re.sub(r"\s+", " ", expr).strip().rstrip(";").strip()
    if len(s) <= max_len:
        return s, False
    cut = s[:max_len].rsplit(" ", 1)[0]
    if len(cut) < max_len // 2:
        cut = s[:max_len]
    return cut.strip(), True


def _consume_balanced_group(tokens: list[str], start_idx: int) -> tuple[list[str], int]:
    """Consume a balanced `(...)` group starting at start_idx."""
    depth = 0
    collected: list[str] = []
    idx = start_idx
    while idx < len(tokens):
        tok = tokens[idx]
        if tok == "(":
            depth += 1
        elif tok == ")":
            depth -= 1
            if depth == 0:
                idx += 1
                break
        if not (depth == 1 and tok == "(" and not collected):
            collected.append(tok)
        idx += 1
    return collected, idx


def _render_tokens(tokens: list[str], sentinels: dict[str, str]) -> str:
    out: list[str] = []
    last_has_sup = False
    can_be_base = False

    def emit(tex: str, *, has_sup: bool = False, is_base: bool = False) -> None:
        nonlocal last_has_sup, can_be_base
        out.append(tex)
        last_has_sup = has_sup
        can_be_base = is_base

    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]

        if tok in sentinels:
            emit(sentinels[tok], has_sup=False, is_base=True)
            i += 1
            continue

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
                inner_toks, next_i = _consume_balanced_group(tokens, i + 1)
                exp_tex = _render_tokens(inner_toks, sentinels) if inner_toks else r"\cdot"
                i = next_i
            elif nxt == "-" and i + 2 < n:
                if tokens[i + 2] == "(":
                    inner_toks, next_i = _consume_balanced_group(tokens, i + 2)
                    exp_tex = "-" + (_render_tokens(inner_toks, sentinels) if inner_toks else r"\cdot")
                    i = next_i
                else:
                    atom_tex = _render_tokens([tokens[i + 2]], sentinels)
                    exp_tex = f"-{atom_tex}"
                    i += 3
            elif nxt in (")", "]", "}", "⟩", ",", ";", "="):
                # Malformed/truncated exponent right before closing delimiter
                emit(r"\text{\^{}}", has_sup=False, is_base=False)
                i += 1
                continue
            else:
                exp_tex = _render_tokens([nxt], sentinels)
                i += 2

            if base_prefix:
                emit(f"{base_prefix}^{{{exp_tex}}}", has_sup=True, is_base=True)
            else:
                out[-1] = f"{out[-1]}^{{{exp_tex}}}"
                last_has_sup = True
                can_be_base = True
            continue

        # Multi-character Lean operators & delimiters
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
        elif tok == "²":
            if out and can_be_base:
                if last_has_sup:
                    out[-1] = "{" + out[-1] + "}"
                out[-1] = f"{out[-1]}^{{2}}"
                last_has_sup = True
                can_be_base = True
            else:
                emit(r"(\cdot)^{2}", has_sup=True, is_base=True)
        elif tok == "³":
            if out and can_be_base:
                if last_has_sup:
                    out[-1] = "{" + out[-1] + "}"
                out[-1] = f"{out[-1]}^{{3}}"
                last_has_sup = True
                can_be_base = True
            else:
                emit(r"(\cdot)^{3}", has_sup=True, is_base=True)
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
        elif tok in _MATH_UNICODE_MAP:
            tex = _MATH_UNICODE_MAP[tok]
            is_closing = tok in ("⌋", "⌉", "⟩", "›", "∅", "ℕ", "ℤ", "ℚ", "ℝ", "ℂ", "∞")
            emit(tex, has_sup=False, is_base=is_closing or (tok in ("ε", "δ", "μ", "π", "α", "β", "γ", "θ", "λ", "σ", "τ", "φ", "ψ", "ω")))
        elif tok[0].isdigit():
            emit(tok, has_sup=False, is_base=True)
        elif tok[0].isalpha() or tok[0] == "_":
            frag, has_sup, is_base = _format_ident(tok)
            emit(frag, has_sup=has_sup, is_base=is_base)
        elif ord(tok[0]) > 127:
            emit(r"\text{" + escape_latex_text(tok) + "}", has_sup=False, is_base=True)
        else:
            emit(tok, has_sup=False, is_base=tok in (")", "]", "!"))

        i += 1

    return " ".join(out)


def validate_katex_safety(latex: str) -> list[str]:
    """
    Validate structural KaTeX safety (balanced braces, no unescaped %,
    no unescaped math operators inside \\text{}/\\texttt{}, no dangling _ or ^).
    """
    issues: list[str] = []
    n = len(latex)
    brace_depth = 0
    i = 0

    while i < n:
        ch = latex[i]
        if ch == "\\":
            if i + 1 < n and not latex[i + 1].isalpha():
                i += 2
                continue
            # Scan macro name
            j = i + 1
            while j < n and latex[j].isalpha():
                j += 1
            macro = latex[i + 1 : j]
            if macro in ("text", "texttt", "textbf", "textit") and j < n and latex[j] == "{":
                # Verify contents of text-mode group
                t_depth = 1
                k = j + 1
                while k < n and t_depth > 0:
                    tc = latex[k]
                    if tc == "\\":
                        k += 2
                        continue
                    if tc == "{":
                        t_depth += 1
                    elif tc == "}":
                        t_depth -= 1
                    elif tc in ("_", "^", "$", "#", "&", "%"):
                        issues.append(f"Unescaped '{tc}' inside \\{macro}{{...}} at pos {k}")
                    elif ord(tc) > 127:
                        issues.append(f"Non-ASCII '{tc}' inside \\{macro}{{...}} at pos {k}")
                    k += 1
                if t_depth != 0:
                    issues.append(f"Unclosed \\{macro}{{...}} group")
                i = k
                continue
            i = j
            continue

        if ch == "{":
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth < 0:
                issues.append(f"Unexpected '}}' at pos {i}")
                break
        elif ch == "%":
            issues.append(f"Unescaped '%' at pos {i}")
        elif ch in ("_", "^"):
            rest = latex[i + 1 :].lstrip()
            if not rest or rest[0] in ("}", ")"):
                issues.append(f"Dangling '{ch}' at pos {i}")
        i += 1

    if brace_depth > 0:
        issues.append(f"Unclosed '{{' (depth={brace_depth})")

    return issues


def lean_expr_to_latex(expr: str, max_len: int = 360) -> str:
    """
    Best-effort syntactic translation of a Lean 4 proposition or term into
    guaranteed KaTeX-safe LaTeX math mode.
    """
    if not expr or not expr.strip():
        return r"\cdot"

    truncated_raw, was_truncated = _truncate_cleanly(expr, max_len)
    sentinels: dict[str, str] = {}
    counter = 0

    def next_sentinel(tex: str) -> str:
        nonlocal counter
        key = f"__LIT_SENTINEL_{counter}__"
        counter += 1
        sentinels[key] = tex
        return f" {key} "

    # Structured multi-token pre-normalizations
    s = re.sub(
        r"=o\[Filter\.atTop\]",
        lambda _: next_sentinel(r"= o_{\infty}"),
        truncated_raw,
    )
    s = re.sub(
        r"=o\[([^\]]+)\]",
        lambda m: next_sentinel(rf"= o_{{{lean_expr_to_latex(m.group(1), max_len=60)}}}"),
        s,
    )
    s = re.sub(
        r"\[MOD\s+([^\]]+)\]",
        lambda m: next_sentinel(rf"\pmod{{{lean_expr_to_latex(m.group(1), max_len=60)}}}"),
        s,
    )

    tokens = _EXPR_TOKEN_RE.findall(s)
    rendered = _render_tokens(tokens, sentinels)
    rendered = re.sub(r"\s+", " ", rendered).strip()
    # Tighten punctuation spacing for readability
    rendered = re.sub(r"\(\s+", "(", rendered)
    rendered = re.sub(r"\s+\)", ")", rendered)
    rendered = re.sub(r"\s+,", ",", rendered)
    rendered = re.sub(r"\s+:", ":", rendered)

    if was_truncated:
        rendered = f"{rendered}\\; \\ldots"

    if not rendered or validate_katex_safety(rendered):
        return rf"\texttt{{{escape_latex_code(expr, max_len=min(max_len, 180))}}}"

    return rendered
