"""forbidden-alias — a manifest value referred to by a forbidden alias.

When the manifest declares ``label_aliases_forbidden: ["accuracy"]`` for
``exact_accuracy``, the report must not call the value "accuracy". This is
not a style preference: the author has decided the alias is misleading
(e.g., "accuracy" without qualification implies top-1, but the value is
exact match).

The check is case-insensitive but whole-word — ``"accuracy"`` doesn't
match the word ``inaccuracy``.
"""

from __future__ import annotations

import re

from scitexlintr._doc import TexDoc, phrase_pattern
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "forbidden-alias"


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()
    fmt = getattr(doc, "fmt", "tex")
    for entry in manifest.numbers:
        # Spans where the approved label itself appears: an alias inside one
        # ("accuracy" within "exact match accuracy") is not a forbidden use.
        canonical_spans = []
        if entry.label_canonical and entry.label_canonical.strip():
            canonical_re = phrase_pattern(entry.label_canonical, fmt, re.IGNORECASE, boundary="[A-Za-z]")
            canonical_spans = [(c.start(), c.end()) for c in
                               canonical_re.finditer(doc.stripped, doc.body_start, doc.body_end)]
        for alias in entry.label_aliases_forbidden:
            if not alias.strip():
                continue
            pattern = phrase_pattern(alias, fmt, re.IGNORECASE, boundary="[A-Za-z]")
            for m in pattern.finditer(doc.stripped, doc.body_start, doc.body_end):
                if not doc.in_prose(m.start()):
                    continue
                if any(a <= m.start() and m.end() <= b for a, b in canonical_spans):
                    continue
                key = (m.start(), alias.lower())
                if key in seen:
                    continue
                seen.add(key)
                line, col = doc.lookup(m.start())
                findings.append(
                    Finding(
                        rule=CODE,
                        line=line,
                        col=col,
                        message=(
                            f"forbidden alias {alias!r} for manifest id={entry.id} "
                            f"(canonical label: {entry.label_canonical!r})"
                        ),
                        severity="error",
                    )
                )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=True)
