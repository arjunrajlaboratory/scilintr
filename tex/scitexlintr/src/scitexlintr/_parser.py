"""Tiny, dependency-free TeX scanner.

We do NOT try to be a full LaTeX parser. We need exactly four things:

1. **Comment stripping.** Replace every comment region (unescaped ``%`` to
   end of line) with spaces, so the byte offsets of everything else stay
   valid.
2. **Body extraction.** Find ``\\begin{document}`` and ``\\end{document}``
   so rules don't fire on the preamble.
3. **Macro-call enumeration.** Find ``\\name[opt]{arg}{arg}...`` with
   balanced-brace argument scanning.
4. **Line/column lookup.** Turn a byte offset into a 1-indexed
   (line, col) pair for findings.

That's it. Anything more ambitious (verbatim environments, \\catcode tricks,
exotic spacing) is out of scope for v0.1 — the linter targets straightforward
report.tex files emitted by upstream tooling, not arbitrary TeX.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Arg:
    """A balanced ``{...}`` or ``[...]`` argument region.

    ``start`` is the offset of the opening brace; ``end`` is the offset
    AFTER the closing brace. ``text`` is the raw content between them
    (not including the braces).
    """
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class MacroCall:
    name: str
    # name_start points at the backslash; name_end points after the last
    # letter of the macro name.
    name_start: int
    name_end: int
    args: tuple[Arg, ...]              # ``{...}`` groups
    optional_args: tuple[Arg, ...]     # ``[...]`` groups


_MACRO_NAME_RE = re.compile(r"\\([A-Za-z@]+)\*?")


_VERB_INLINE_RE = re.compile(r"\\verb\*?(?P<delim>[^A-Za-z*\s])")
_VERBATIM_OPEN_RE = re.compile(r"\\begin\s*\{(verbatim\*?|lstlisting|minted)\}")


def strip_comments(source: str) -> str:
    """Return a copy of ``source`` with every comment region replaced by spaces.

    Newlines are preserved so line numbers are unchanged. Comment characters
    are replaced by spaces (not removed) so byte offsets are stable —
    findings reported against the stripped string still point at the right
    location in the original.

    TeX rule: ``%`` starts a comment unless preceded by an odd number of
    backslashes (``\\%`` is a literal percent; ``\\\\%`` is again a comment).

    Verbatim regions — ``\\verb|...|`` inline and ``\\begin{verbatim}...
    \\end{verbatim}`` (plus ``lstlisting`` and ``minted``) — are skipped
    entirely. ``%`` inside verbatim is a literal percent, not a comment.
    """
    out = list(source)
    verbatim_ranges = _find_verbatim_ranges(source)
    in_verbatim = _make_range_check(verbatim_ranges)

    i = 0
    n = len(source)
    while i < n:
        if in_verbatim(i):
            i += 1
            continue
        ch = source[i]
        if ch == "%":
            # Count backslashes immediately to the left.
            bs = 0
            j = i - 1
            while j >= 0 and source[j] == "\\":
                bs += 1
                j -= 1
            if bs % 2 == 0:
                # Real comment — blank out everything up to (but not
                # including) the next newline.
                k = i
                while k < n and source[k] != "\n":
                    out[k] = " "
                    k += 1
                i = k
                continue
        i += 1
    return "".join(out)


def _find_verbatim_ranges(source: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    # Inline \verb<delim>...<delim>. The delimiter is whatever non-letter,
    # non-whitespace, non-* character follows \verb (or \verb*).
    for m in _VERB_INLINE_RE.finditer(source):
        delim = m.group("delim")
        start = m.start()
        end = source.find(delim, m.end())
        if end < 0:
            ranges.append((start, len(source)))
        else:
            ranges.append((start, end + 1))
    # Block verbatim environments.
    for m in _VERBATIM_OPEN_RE.finditer(source):
        env = m.group(1)
        close = re.compile(r"\\end\s*\{" + re.escape(env) + r"\}").search(source, m.end())
        if close is None:
            ranges.append((m.start(), len(source)))
        else:
            ranges.append((m.start(), close.end()))
    ranges.sort()
    return ranges


def _make_range_check(ranges: list[tuple[int, int]]):
    """Return a function that tells whether an offset is inside any range."""
    if not ranges:
        return lambda i: False

    import bisect
    starts = [r[0] for r in ranges]

    def in_range(i: int) -> bool:
        idx = bisect.bisect_right(starts, i) - 1
        if idx < 0:
            return False
        s, e = ranges[idx]
        return s <= i < e

    return in_range


def find_body_range(stripped: str) -> tuple[int, int]:
    """Return the [start, end) byte range of the document body.

    ``start`` is just after the closing brace of ``\\begin{document}``;
    ``end`` is the offset of ``\\end{document}`` (or ``len(stripped)`` if
    no such marker exists). If ``\\begin{document}`` is missing the whole
    file is treated as body — small fragments still lint.
    """
    begin = _find_environment_open(stripped, "document")
    if begin is None:
        return 0, len(stripped)
    end = _find_environment_close(stripped, "document", search_from=begin)
    if end is None:
        end = len(stripped)
    return begin, end


def _find_environment_open(stripped: str, env: str) -> int | None:
    pattern = re.compile(r"\\begin\s*\{" + re.escape(env) + r"\}")
    m = pattern.search(stripped)
    if not m:
        return None
    return m.end()


def _find_environment_close(stripped: str, env: str, *, search_from: int) -> int | None:
    pattern = re.compile(r"\\end\s*\{" + re.escape(env) + r"\}")
    m = pattern.search(stripped, search_from)
    if not m:
        return None
    return m.start()


def find_macro_calls(
    stripped: str, names: set[str] | None = None, *, scope: tuple[int, int] | None = None
) -> list[MacroCall]:
    """Enumerate macro invocations.

    Pass ``names`` to restrict to specific macro names (without the leading
    backslash). Pass ``scope=(start, end)`` to limit the search to a
    sub-range — used to walk the body and ignore the preamble.

    The function returns calls in document order. Nested invocations are
    NOT returned as separate calls automatically: only top-level matches
    found by the regex appear. Callers who need to recurse into argument
    text should do so themselves (and call ``find_macro_calls`` again on
    the argument body).
    """
    start_pos, end_pos = scope if scope else (0, len(stripped))
    calls: list[MacroCall] = []

    for m in _MACRO_NAME_RE.finditer(stripped, start_pos, end_pos):
        name = m.group(1)
        if names is not None and name not in names:
            continue
        cursor = m.end()
        optional_args: list[Arg] = []
        args: list[Arg] = []
        # Greedily consume any [opt] groups, then any {arg} groups,
        # allowing whitespace between them.
        while cursor < end_pos:
            cursor_ws = _skip_whitespace(stripped, cursor, end_pos)
            if cursor_ws >= end_pos:
                break
            ch = stripped[cursor_ws]
            if ch == "[":
                inner_end = _find_matching(stripped, cursor_ws, "[", "]", end_pos)
                if inner_end is None:
                    break
                optional_args.append(
                    Arg(
                        text=stripped[cursor_ws + 1 : inner_end],
                        start=cursor_ws,
                        end=inner_end + 1,
                    )
                )
                cursor = inner_end + 1
                continue
            if ch == "{":
                inner_end = _find_matching(stripped, cursor_ws, "{", "}", end_pos)
                if inner_end is None:
                    break
                args.append(
                    Arg(
                        text=stripped[cursor_ws + 1 : inner_end],
                        start=cursor_ws,
                        end=inner_end + 1,
                    )
                )
                cursor = inner_end + 1
                continue
            break
        calls.append(
            MacroCall(
                name=name,
                name_start=m.start(),
                name_end=m.end(),
                args=tuple(args),
                optional_args=tuple(optional_args),
            )
        )
    return calls


def _skip_whitespace(s: str, start: int, end: int) -> int:
    """Skip TeX-significant whitespace between a macro and its args.

    Spaces, tabs, and a *single* newline are skippable. A blank line —
    two newlines in a row — acts as ``\\par`` in TeX and terminates
    argument scanning. We mirror that: stop at the second newline so
    ``\\foo\\n\\nbody`` does not pull ``body`` in as an argument.
    """
    i = start
    newlines = 0
    while i < end:
        ch = s[i]
        if ch in " \t\r":
            i += 1
        elif ch == "\n":
            newlines += 1
            if newlines > 1:
                break
            i += 1
        else:
            break
    return i


def _find_matching(s: str, open_at: int, open_ch: str, close_ch: str, end: int) -> int | None:
    """Return the offset of the matching ``close_ch`` for the ``open_ch`` at
    ``open_at``, or None if no match is found before ``end``.

    A backslash escapes the next character so ``\\}`` does not close a brace
    group. Nested ``{...}`` inside are tracked by depth.
    """
    assert s[open_at] == open_ch
    depth = 0
    i = open_at
    while i < end:
        ch = s[i]
        if ch == "\\" and i + 1 < end:
            i += 2
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def line_col_lookup(source: str):
    """Return a function mapping byte offset → (line, col), both 1-indexed."""
    # Precompute line starts.
    line_starts = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            line_starts.append(i + 1)

    import bisect

    def lookup(offset: int) -> tuple[int, int]:
        idx = bisect.bisect_right(line_starts, offset) - 1
        if idx < 0:
            idx = 0
        line = idx + 1
        col = offset - line_starts[idx] + 1
        return line, col

    return lookup


# ---------------------------------------------------------------------------
# Prose mask
# ---------------------------------------------------------------------------

# Arguments of these macros are NOT prose (they are paths, labels, refs,
# definitions, structural markers — not text that the linter should scan
# for raw values, thresholds, etc.).
STRUCTURAL_ARG_MACROS: frozenset[str] = frozenset({
    "includegraphics",
    "label", "ref", "pageref", "eqref", "autoref", "cref", "Cref",
    "cite", "citet", "citep", "citeauthor", "citeyear", "Citet", "Citep",
    "input", "include", "InputIfFileExists",
    "begin", "end",
    "newcommand", "renewcommand", "providecommand", "def",
    "documentclass", "usepackage", "RequirePackage",
    "bibliographystyle", "bibliography",
    "url", "href",
})

# For the wrapper macros we treat BOTH arguments as non-prose for numeric
# scanning. (The first arg is a macro name; the second is the snapshot,
# which we check via the snapshot-mismatch rule rather than treating as
# free-form prose.)
WRAPPER_MACROS: frozenset[str] = frozenset({"SciVal", "SciText"})


def build_prose_mask(stripped: str, body_start: int, body_end: int) -> bytearray:
    """Return a bytearray of length ``len(stripped)`` marking prose bytes.

    Byte i is 1 iff the byte at offset i counts as prose for the numeric
    scanners (raw-generated-value, unsourced-numeric-token,
    handwritten-numeric-claim, magic-tex-threshold).

    The preamble, macro names, and arguments of structural / wrapper macros
    are all 0.
    """
    mask = bytearray(len(stripped))
    # Everything in body starts as prose; preamble stays 0.
    for i in range(body_start, body_end):
        mask[i] = 1

    # Walk macros in the body and clear their NAME tokens and structural
    # / wrapper argument regions.
    for call in find_macro_calls(stripped, names=None, scope=(body_start, body_end)):
        # Macro name itself is not prose.
        for i in range(call.name_start, call.name_end):
            mask[i] = 0
        if call.name in STRUCTURAL_ARG_MACROS or call.name in WRAPPER_MACROS:
            for arg in call.args:
                for i in range(arg.start, arg.end):
                    mask[i] = 0
            for opt in call.optional_args:
                for i in range(opt.start, opt.end):
                    mask[i] = 0
        # For all other macros, the macro NAME is non-prose but arguments
        # remain prose — \emph{317} keeps "317" scannable.
    return mask
