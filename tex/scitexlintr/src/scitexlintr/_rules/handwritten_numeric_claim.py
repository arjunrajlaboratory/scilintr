"""handwritten-numeric-claim — hand-typed ``n = 23``, ``p = 1e-8``, ``r = 0.82``.

Catches the canonical sources of drift: somebody types a result-shaped
phrase into the prose instead of pulling it from the manifest. The
single-letter prefix anchors the match (``n``, ``p``, ``r``, case-insensitive)
so that ``\\alpha = 0.05`` and ``Section 4.2`` don't trigger.

Manifest-free — fires whether or not a manifest is provided. Pair with the
``\\SciVal`` wrapper convention for the fix.
"""

from __future__ import annotations

import re

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "handwritten-numeric-claim"

# A handwritten claim looks like ``n = 23``, ``p < 0.05``, ``r = 0.82``.
# We require:
#   * a single-letter prefix from {n N p P r R}, with a word boundary before it
#   * optional whitespace + (=|<|>) + optional whitespace
#   * a numeric token (incl. scientific notation)
# We restrict to single-letter prefixes so that ``Bagamery n=23`` matches
# but ``mean=23`` does not.
_PATTERN = re.compile(
    r"(?<![A-Za-z@\\])"
    r"(?P<prefix>[nNpPrR])"
    r"\s*=\s*"
    r"(?P<num>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)"
)


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    findings: list[Finding] = []
    for m in _PATTERN.finditer(doc.stripped, doc.body_start, doc.body_end):
        # Must be in prose (not inside structural macro args).
        if not doc.in_prose(m.start("prefix")):
            continue
        line, col = doc.lookup(m.start("prefix"))
        findings.append(
            Finding(
                rule=CODE,
                line=line,
                col=col,
                message=(
                    f"handwritten numeric claim {m.group(0)!r} — "
                    f"register the value with register_value() and wrap"
                ),
                severity="warning",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=False)
