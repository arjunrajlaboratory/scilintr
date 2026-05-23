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

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "forbidden-alias"


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    findings: list[Finding] = []
    seen: set[tuple[int, str]] = set()
    for entry in manifest.numbers:
        canonical = (entry.label_canonical or "").lower()
        for alias in entry.label_aliases_forbidden:
            if not alias.strip():
                continue
            pattern = re.compile(
                r"(?<![A-Za-z])" + re.escape(alias) + r"(?![A-Za-z])",
                re.IGNORECASE,
            )
            for m in pattern.finditer(doc.stripped, doc.body_start, doc.body_end):
                if not doc.in_prose(m.start()):
                    continue
                if canonical and _alias_is_inside_canonical(
                    doc.stripped, m.start(), m.end(), canonical
                ):
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


def _alias_is_inside_canonical(text: str, start: int, end: int, canonical_lc: str) -> bool:
    """Return True if the alias span at [start, end) is a substring of the
    canonical label appearing at the same location in ``text``.

    ``"accuracy"`` inside ``"exact match accuracy"`` should not fire; that
    IS the approved label, not a bare alias.
    """
    alias_lc = text[start:end].lower()
    pos = canonical_lc.find(alias_lc)
    if pos < 0:
        return False
    window_start = max(0, start - pos)
    window_end = window_start + len(canonical_lc)
    if window_end > len(text):
        return False
    return text[window_start:window_end].lower() == canonical_lc


rule = Rule(code=CODE, check=_check, requires_manifest=True)
