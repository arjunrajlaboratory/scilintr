"""script-data-literal — numeric data typed into a report script.

Interactive figures must draw from registered, fingerprinted data blocks
(``unfingerprinted-data``). A script that carries its own data sidesteps
that check, so any array literal holding six or more numbers as values — a
flat array, an array of point pairs, an array of ``{x, y}`` objects, with or
without a trailing comma — is flagged. Strings and comments are ignored.
Only numbers in value positions count (after ``[``, ``,`` or ``:`` and before
``,``, ``]`` or ``}``), and an index access such as ``cols[0]`` is not an
array literal, so indexes, call arguments (``toFixed(1)``), margins, and
tick steps stay below the threshold.

The first ``<script id="sci-report-runtime">`` (the shared runtime that
``check_html_report.py`` compares against the template) is exempt; any other
script is not, whatever its id.

HTML only. Warning: legitimate constants exist; waive them inside the script
with ``// ANALYSIS_OK[script-data-literal]: reason``.
"""

from __future__ import annotations

import re

from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "script-data-literal"
MIN_NUMBERS = 6
# A number in a value position: after "[", "," or ":" and before ",", "]" or "}".
_VALUE_NUMBER_RE = re.compile(
    r"(?<=[\[,:])\s*[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?\s*(?=[,\]}])"
)
_INDEX_OPENER_RE = re.compile(r"[\w$)\]]\s*$")
# A bracket after one of these keywords starts an array literal, not an
# index access: `return [1, 2, 3]`, `yield [...]`, `case [...]`.
_KEYWORDS_BEFORE_LITERAL = frozenset({
    "return", "yield", "await", "typeof", "case", "in", "of", "new", "delete",
    "void", "throw", "else", "do", "instanceof", "default",
})
# The keyword must stand alone: after a "." it is a property (obj.default[0]).
_LAST_WORD_RE = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*$")


def _is_index_opener(before: str) -> bool:
    if not _INDEX_OPENER_RE.search(before):
        return False
    word = _LAST_WORD_RE.search(before)
    return not (word and word.group(1) in _KEYWORDS_BEFORE_LITERAL)


def blank_strings_and_comments(js: str) -> str:
    """``js`` with string literals and comments replaced by spaces
    (same length, newlines kept). Template-literal interpolations are
    blanked too; regex literals are not recognized (rare in report code)."""
    out = list(js)
    i, n = 0, len(js)

    def blank(a: int, b: int) -> None:
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        ch = js[i]
        if js.startswith("//", i):
            j = js.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
        elif js.startswith("/*", i):
            j = js.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
        elif ch in "'\"`":
            j = i + 1
            while j < n and js[j] != ch:
                j += 2 if js[j] == "\\" else 1
            blank(i, j + 1)
            i = j + 1
        else:
            i += 1
    return "".join(out)


def _blank_index_accesses(code: str) -> str:
    """``code`` with the contents of index accesses (``a[0]``, ``f()[i]``)
    blanked, so only array literals remain bracketed."""
    out = list(code)
    stack: list[tuple[int, bool]] = []
    for i, ch in enumerate(code):
        if ch == "[":
            stack.append((i, _is_index_opener(code[max(0, i - 40):i])))
        elif ch == "]" and stack:
            start, is_index = stack.pop()
            if is_index:
                for k in range(start, i + 1):
                    if out[k] != "\n":
                        out[k] = " "
    return "".join(out)


def _outer_bracket_groups(code: str):
    depth, start = 0, None
    for i, ch in enumerate(code):
        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]" and depth:
            depth -= 1
            if depth == 0:
                yield start, i + 1


def _check(doc, manifest: Manifest | None) -> list[Finding]:
    if getattr(doc, "fmt", "tex") != "html":
        return []
    findings: list[Finding] = []
    for script in doc.scripts:
        if script.runtime:
            continue
        code = _blank_index_accesses(blank_strings_and_comments(script.text))
        for a, b in _outer_bracket_groups(code):
            count = len(_VALUE_NUMBER_RE.findall(code, a, b))
            if count >= MIN_NUMBERS:
                line, col = doc.lookup(script.body_start + a)
                findings.append(
                    Finding(
                        rule=CODE, line=line, col=col, severity="warning",
                        message=(f"literal with {count} numbers in a report script; draw interactive "
                                 "figures from a registered data-sci-data block instead"),
                    )
                )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=False)
