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
        # Search for the warning text anywhere up to (and including) the
        # first mention.
        warning_idx = doc.stripped.find(
            term.overloaded_warning, doc.body_start, first_match.end()
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


rule = Rule(code=CODE, check=_check, requires_manifest=True)
