"""overloaded-term-no-warning — a term flagged ``overloaded_warning`` is
used in prose before its warning text appears.

Some terms collide with stronger or weaker variants in the literature
(BCLRT vs. a Wilks-sense LRT, for instance). The manifest carries the
warning text the author committed to; if the first prose mention precedes
that warning, the reader is being shown the term without its disambiguation.

We only fire on the FIRST occurrence-before-warning per term. Subsequent
mentions are considered "the warning was already issued" and pass.
"""

from __future__ import annotations

import re

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "overloaded-term-no-warning"


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    findings: list[Finding] = []
    for term in manifest.terms:
        if not term.overloaded_warning:
            continue
        # Find first prose occurrence of the term.
        term_re = re.compile(r"(?<![A-Za-z@])" + re.escape(term.id) + r"(?![A-Za-z@])")
        first_match = None
        for m in term_re.finditer(doc.stripped, doc.body_start, doc.body_end):
            if doc.in_prose(m.start()):
                first_match = m
                break
        if first_match is None:
            continue
        # Acceptable warning placements: anywhere BEFORE the first mention,
        # OR within the same SENTENCE as the first mention (so an
        # in-sentence disambiguation right after the term counts). A
        # sentence ends at the next `.`, `!`, or `?` followed by
        # whitespace, a newline, or end of body.
        sentence_end = _sentence_end(doc.stripped, first_match.end(), doc.body_end)
        warning_idx = doc.stripped.find(
            term.overloaded_warning, doc.body_start, sentence_end
        )
        if warning_idx >= 0:
            continue
        line, col = doc.lookup(first_match.start())
        findings.append(
            Finding(
                rule=CODE,
                line=line,
                col=col,
                message=(
                    f"first mention of overloaded term {term.id!r} precedes "
                    f"its required warning: {term.overloaded_warning!r}"
                ),
                severity="warning",
            )
        )
    return findings


def _sentence_end(text: str, start: int, body_end: int) -> int:
    """Return the offset of the end of the sentence beginning at ``start``.

    A sentence ends at the first ``.``, ``!``, or ``?`` followed by
    whitespace, a newline, or end of body. ``body_end`` is the upper
    bound; we never look past it.
    """
    i = start
    while i < body_end:
        ch = text[i]
        if ch in ".!?":
            j = i + 1
            if j >= body_end:
                return j
            nxt = text[j]
            if nxt in " \t\n\r":
                return j
        if ch == "\n":
            j = i + 1
            while j < body_end and text[j] in " \t":
                j += 1
            if j < body_end and text[j] == "\n":
                # Blank line ends the sentence even without a terminator.
                return i
            i = j
            continue
        i += 1
    return body_end


rule = Rule(code=CODE, check=_check, requires_manifest=True)
