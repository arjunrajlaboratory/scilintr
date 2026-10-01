"""Detect ``ANALYSIS_OK[category]: explanation`` waivers in TeX and HTML sources.

TeX: ``% ANALYSIS_OK[…]: …`` comments. HTML: ``<!-- ANALYSIS_OK[…]: … -->``
comments, and inside ``<script>`` elements ``// ANALYSIS_OK[…]: …`` or
``/* ANALYSIS_OK[…]: … */`` JavaScript comments.

Mirror of scilintr's Python waiver pattern, adapted to TeX comment syntax:

* The waiver must live inside a real TeX comment (unescaped ``%``).
* It must name one or more rule codes in square brackets, comma-separated
  (``ANALYSIS_OK[raw-generated-value, unsourced-numeric-token]``).
* It must include a colon and a non-empty explanation.

A waiver on line L suppresses findings on lines L..L+4 — the same forward
window scilintr uses, so authors don't have to learn two conventions.

A **region waiver** covers every line from its ``ANALYSIS_OK_BEGIN[…]: …``
comment through the matching ``ANALYSIS_OK_END[…]``, which closes the
innermost open region naming all of its rule codes (a bare
``ANALYSIS_OK_END`` closes the innermost region). The BEGIN needs an
explanation; the END may carry trailing text (``: end of table 3``). A BEGIN with no END waives nothing,
so a forgotten END surfaces as findings rather than silently waiving the
rest of the file.

HTML sources spell the same waivers as comments,
``<!-- ANALYSIS_OK[category]: explanation -->``. A multi-line HTML comment
counts from the line it ends on. ``%`` means nothing in HTML, so a
TeX-style waiver in an HTML file is ordinary text and waives nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CATS = r"(?P<categories>[\w-]+(?:\s*,\s*[\w-]+)*)"
_EXPL = r":\s*(?P<explanation>\S.*?)\s*$"

# Bodies of a comment (after `%`, `<!--`, `//` or `/*`), matched at its start.
_LINE_BODY_RE = re.compile(r"ANALYSIS_OK\[" + _CATS + r"\]" + _EXPL, re.S)
_BEGIN_BODY_RE = re.compile(r"ANALYSIS_OK_BEGIN\[" + _CATS + r"\]" + _EXPL, re.S)
_END_BODY_RE = re.compile(r"ANALYSIS_OK_END(?:\[" + _CATS + r"\])?(?:\s*:.*|\s*)$", re.S)

DEFAULT_WINDOW = 4


@dataclass(frozen=True)
class Waiver:
    line: int
    category: str                      # the first rule code named
    explanation: str
    categories: tuple[str, ...] = ()   # every rule code named (defaults to ``(category,)``)
    end_line: int | None = None        # set for a region waiver: covers line..end_line

    def covers(self, rule: str) -> bool:
        return rule in (self.categories or (self.category,))


def _split(categories: str) -> tuple[str, ...]:
    return tuple(c.strip() for c in categories.split(","))


@dataclass(frozen=True)
class _Event:
    line: int
    kind: str                  # "line" | "begin" | "end"
    categories: tuple[str, ...]
    explanation: str = ""


def _event(body: str, line: int) -> _Event | None:
    """Classify a comment body (text after the comment opener)."""
    body = body.strip()
    if body.endswith("*/"):
        body = body[:-2]
    if body.endswith("-->"):
        body = body[:-3]
    for kind, rx in (("line", _LINE_BODY_RE), ("begin", _BEGIN_BODY_RE)):
        m = rx.match(body)
        if m:
            return _Event(line, kind, _split(m.group("categories")),
                          " ".join(m.group("explanation").split()))
    m = _END_BODY_RE.match(body)
    if m:
        cats = m.group("categories")
        return _Event(line, "end", _split(cats) if cats else ())
    return None


def _assemble(events: list[_Event]) -> list[Waiver]:
    """Turn line waivers into ``Waiver``s and pair BEGIN/END into regions."""
    waivers: list[Waiver] = []
    open_regions: list[_Event] = []
    for ev in sorted(events, key=lambda e: e.line):
        if ev.kind == "line":
            waivers.append(Waiver(ev.line, ev.categories[0], ev.explanation, ev.categories))
        elif ev.kind == "begin":
            open_regions.append(ev)
        else:
            for i in range(len(open_regions) - 1, -1, -1):
                if set(ev.categories) <= set(open_regions[i].categories):
                    b = open_regions.pop(i)
                    waivers.append(Waiver(b.line, b.categories[0], b.explanation,
                                          b.categories, end_line=ev.line))
                    break
    return waivers


def find_waivers(source: str) -> list[Waiver]:
    """Return every well-formed waiver in ``source``.

    The match runs against the raw line — escaped ``\\%`` cannot start a
    comment, so we walk character-by-character to find the first unescaped
    ``%`` before applying the regex. Anything before that ``%`` is prose,
    not comment.
    """
    events: list[_Event] = []
    for line_no, line in enumerate(source.splitlines(), start=1):
        comment_start = _find_comment_start(line)
        if comment_start is None:
            continue
        for m in _TEX_OPENER_RE.finditer(line, comment_start):
            ev = _event(line[m.end():], line_no)
            if ev is not None:
                events.append(ev)
                break
    return _assemble(events)


# A `%` (TeX) or `//` / `/*` (JS) immediately followed by a waiver keyword;
# the waiver body runs to the end of that line.
_TEX_OPENER_RE = re.compile(r"%\s*(?=ANALYSIS_OK)")
_JS_OPENER_RE = re.compile(r"(?://|/\*)\s*(?=ANALYSIS_OK)")


def find_html_waivers(doc) -> list[Waiver]:
    """Waivers in an HTML document's comments (see ``_html.HtmlDoc.comments``)
    and, inside ``<script>`` elements, in JavaScript comments
    (``// ANALYSIS_OK[rule]: …`` or ``/* ANALYSIS_OK[rule]: … */``) — an HTML
    comment cannot appear inside a script, so script findings would otherwise
    be unwaivable."""
    events: list[_Event] = []
    for script in getattr(doc, "scripts", ()):
        for m in _JS_OPENER_RE.finditer(script.text):
            eol = script.text.find("\n", m.end())
            body = script.text[m.end(): eol if eol != -1 else len(script.text)]
            line, _ = doc.lookup(script.body_start + m.start())
            ev = _event(body, line)
            if ev is not None:
                events.append(ev)
    for c in doc.comments:
        line, _ = doc.lookup(max(c.end - 1, c.start))
        ev = _event(c.text, line)
        if ev is not None:
            events.append(ev)
    return _assemble(events)


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
    the ``window`` lines ending at the finding's line (or on the same line),
    or if the finding lies inside a region waiver naming its rule code.
    """
    for w in waivers:
        if not w.covers(finding_rule):
            continue
        if w.end_line is not None:
            if w.line <= finding_line <= w.end_line:
                return True
        elif 0 <= finding_line - w.line <= window:
            return True
    return False
