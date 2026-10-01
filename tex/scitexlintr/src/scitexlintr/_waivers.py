"""Detect ``ANALYSIS_OK[category]: explanation`` waivers in TeX and HTML sources.

TeX: ``% ANALYSIS_OK[…]: …`` comments. HTML: ``<!-- ANALYSIS_OK[…]: … -->``
comments, and inside ``<script>`` elements ``// ANALYSIS_OK[…]: …`` or
``/* ANALYSIS_OK[…]: … */`` JavaScript comments.

Mirror of scilintr's Python waiver pattern, adapted to TeX comment syntax:

* The waiver must live inside a real TeX comment (unescaped ``%``).
* It must name a category in square brackets — drawn from the rule catalog,
  although we don't enforce the vocabulary here.
* It must include a colon and a non-empty explanation.

A waiver on line L suppresses findings on lines L..L+4 — the same forward
window scilintr uses, so authors don't have to learn two conventions.

HTML sources spell the same waiver as a comment,
``<!-- ANALYSIS_OK[category]: explanation -->``. A multi-line HTML comment
counts from the line it ends on. ``%`` means nothing in HTML, so a
TeX-style waiver in an HTML file is ordinary text and waives nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WAIVER_RE = re.compile(
    r"%\s*ANALYSIS_OK\[(?P<category>[\w-]+)\]:\s*(?P<explanation>\S.*?)\s*$"
)

DEFAULT_WINDOW = 4


@dataclass(frozen=True)
class Waiver:
    line: int
    category: str
    explanation: str


def find_waivers(source: str) -> list[Waiver]:
    """Return every well-formed waiver in ``source``.

    The match runs against the raw line — escaped ``\\%`` cannot start a
    comment, so we walk character-by-character to find the first unescaped
    ``%`` before applying the regex. Anything before that ``%`` is prose,
    not comment.
    """
    waivers: list[Waiver] = []
    for line_no, line in enumerate(source.splitlines(), start=1):
        comment_start = _find_comment_start(line)
        if comment_start is None:
            continue
        comment_segment = line[comment_start:]
        m = _WAIVER_RE.search(comment_segment)
        if m:
            waivers.append(
                Waiver(
                    line=line_no,
                    category=m.group("category"),
                    explanation=m.group("explanation"),
                )
            )
    return waivers


_HTML_WAIVER_RE = re.compile(
    r"^\s*ANALYSIS_OK\[(?P<category>[\w-]+)\]:\s*(?P<explanation>\S.*?)\s*$", re.S
)


_JS_WAIVER_RE = re.compile(
    r"(?://|/\*)\s*ANALYSIS_OK\[(?P<category>[\w-]+)\]:\s*(?P<explanation>[^\n]*?\S)\s*(?:\*/)?\s*$", re.M
)


def find_html_waivers(doc) -> list[Waiver]:
    """Waivers in an HTML document's comments (see ``_html.HtmlDoc.comments``)
    and, inside ``<script>`` elements, in JavaScript comments
    (``// ANALYSIS_OK[rule]: …`` or ``/* ANALYSIS_OK[rule]: … */``) — an HTML
    comment cannot appear inside a script, so script findings would otherwise
    be unwaivable."""
    waivers: list[Waiver] = []
    for script in getattr(doc, "scripts", ()):
        for m in _JS_WAIVER_RE.finditer(script.text):
            line, _ = doc.lookup(script.body_start + m.start())
            waivers.append(Waiver(line=line, category=m.group("category"), explanation=m.group("explanation")))
    for c in doc.comments:
        m = _HTML_WAIVER_RE.match(c.text)
        if not m:
            continue
        line, _ = doc.lookup(max(c.end - 1, c.start))
        waivers.append(
            Waiver(
                line=line,
                category=m.group("category"),
                explanation=" ".join(m.group("explanation").split()),
            )
        )
    return waivers


def _find_comment_start(line: str) -> int | None:
    """Return the index of the first unescaped ``%`` in ``line``, or None.

    TeX semantics: ``\\%`` is a literal percent and does not start a comment.
    A backslash followed by ``%`` only escapes if the backslash is not itself
    escaped — i.e., an odd number of consecutive backslashes immediately
    before the ``%`` neutralizes it.
    """
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == "%":
            # Count consecutive backslashes immediately to the left.
            bs = 0
            j = i - 1
            while j >= 0 and line[j] == "\\":
                bs += 1
                j -= 1
            if bs % 2 == 0:
                return i
        i += 1
    return None


def is_waived(
    finding_line: int,
    finding_rule: str,
    waivers: list[Waiver],
    window: int = DEFAULT_WINDOW,
) -> bool:
    """A finding is waived if a waiver naming its rule code appears on one of
    the ``window`` lines ending at the finding's line, OR on the same line.
    """
    return any(
        w.category == finding_rule and 0 <= finding_line - w.line <= window
        for w in waivers
    )
