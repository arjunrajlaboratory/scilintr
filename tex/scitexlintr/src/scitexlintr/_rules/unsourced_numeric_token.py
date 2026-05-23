"""unsourced-numeric-token — a numeric in prose that isn't traceable.

Aggressive by design: any numeric token in prose that doesn't match a
manifest value gets a warning. The context heuristics below cut common
false positives that would otherwise drown out the signal — they are
deliberately specific, not "looks like maybe a reference".

A finding here usually means one of:
  * a one-off claim that should be registered with ``register_value()``;
  * a literal copied from somewhere outside the analysis;
  * a section/figure/percentage we forgot to teach the heuristics about
    (in which case: file an issue, don't loosen the rule).
"""

from __future__ import annotations

import re

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest, values_equal_as_snapshot
from scitexlintr._rules._base import Rule

CODE = "unsourced-numeric-token"

# A numeric token. Optional comma-grouping in the integer part keeps
# ``15,122`` together; trailing ``.5`` etc. is allowed.
_NUMBER_RE = re.compile(
    r"(?<![\w.])"
    r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?"
    r"(?![\w.])"
)

# Tokens that, when they precede a number, mean "this is a structural
# reference, not a scientific claim". Match is whole-word, case-insensitive.
_REFERENCE_TOKENS = (
    "section", "sect", "sec",
    "figure", "fig", "figs",
    "table", "tab", "tabs",
    "equation", "eq", "eqs",
    "chapter", "chap",
    "appendix", "app",
    "step", "page", "panel", "supplementary", "supp", "row", "col", "column",
)
_REFERENCE_RE = re.compile(
    r"(?:" + "|".join(_REFERENCE_TOKENS) + r")\.?",
    re.IGNORECASE,
)

# ``[nNpPrRkK] = `` immediately before the number means handwritten claim
# is handling it — don't double-flag.
_HANDWRITTEN_PREFIX_RE = re.compile(r"(?<![A-Za-z@\\])[nNpPrRkK]\s*[=<>]\s*$")


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[int] = set()
    for m in _NUMBER_RE.finditer(doc.stripped, doc.body_start, doc.body_end):
        offset = m.start()
        if offset in seen:
            continue
        if not doc.in_prose(offset):
            continue
        num = m.group(0)

        # Manifest match -> caught by raw-generated-value, not us.
        if manifest is not None and _matches_manifest(manifest, num):
            continue

        # Threshold context -> magic-tex-threshold / unwrapped-threshold.
        if _is_threshold_context(doc.stripped, offset, doc.body_start):
            continue

        # Handwritten n = / p = / r = -> handwritten-numeric-claim.
        if _is_handwritten_context(doc.stripped, offset, doc.body_start):
            continue

        # Tail of a scientific-notation number, e.g. the "8" inside "1e-8".
        if _is_scientific_tail(doc.stripped, offset, doc.body_start):
            continue

        # Section / Figure / Table reference.
        if _is_reference_context(doc.stripped, offset, doc.body_start):
            continue

        # Percentage: trailing ``\%``, ``%``, or `` percent``.
        if _is_percent_context(doc.stripped, m.end(), doc.body_end):
            continue

        seen.add(offset)
        line, col = doc.lookup(offset)
        findings.append(
            Finding(
                rule=CODE,
                line=line,
                col=col,
                message=(
                    f"numeric token {num!r} in prose has no manifest entry — "
                    f"register the value or add a waiver"
                ),
                severity="warning",
            )
        )
    return findings


def _matches_manifest(manifest: Manifest, snap: str) -> bool:
    for entry in manifest.numbers:
        if values_equal_as_snapshot(entry.value, snap):
            return True
    return False


def _is_threshold_context(text: str, offset: int, body_start: int) -> bool:
    # Look back over whitespace; the preceding token must be a comparison
    # operator (plain or LaTeX-spelled).
    i = offset - 1
    while i >= body_start and text[i] in " \t":
        i -= 1
    if i < body_start:
        return False
    if text[i] in "<>":
        return True
    # \le, \leq, \ge, \geq, \ll, \gg
    for cmd in ("\\le", "\\leq", "\\ge", "\\geq", "\\ll", "\\gg"):
        if text.endswith(cmd, body_start, i + 1):
            # And not part of a longer macro name like \lemma.
            after = i + 1
            if after >= len(text) or not (text[after].isalpha() or text[after] == "@"):
                return True
    return False


def _is_handwritten_context(text: str, offset: int, body_start: int) -> bool:
    prefix = text[max(body_start, offset - 8) : offset]
    return _HANDWRITTEN_PREFIX_RE.search(prefix) is not None


def _is_reference_context(text: str, offset: int, body_start: int) -> bool:
    # Look back over whitespace then take the preceding word and check
    # against the reference vocabulary.
    i = offset - 1
    while i >= body_start and text[i] in " \t~":
        i -= 1
    if i < body_start:
        return False
    # Walk back over the word.
    word_end = i + 1
    while i >= body_start and (text[i].isalpha() or text[i] == "."):
        i -= 1
    word = text[i + 1 : word_end].rstrip(".")
    return word.lower() in _REFERENCE_TOKENS


def _is_scientific_tail(text: str, offset: int, body_start: int) -> bool:
    """``1e-8`` — the trailing ``8`` is part of the same number, not a fresh one."""
    if offset - 2 < body_start:
        return False
    if text[offset - 1] not in "+-":
        return False
    if text[offset - 2] not in "eE":
        return False
    # Confirm there's a digit immediately before the e/E (the mantissa).
    if offset - 3 >= body_start and not text[offset - 3].isdigit():
        return False
    return True


def _is_percent_context(text: str, end_offset: int, body_end: int) -> bool:
    # Typographic percent only — ``50\%`` and ``50%`` get skipped, but
    # ``99.9 percent`` is left for the unsourced rule because the
    # spelled-out form usually denotes a result claim, not a casual figure.
    j = end_offset
    while j < body_end and text[j] in " \t":
        j += 1
    if j >= body_end:
        return False
    if text[j] == "%":
        return True
    if text.startswith("\\%", j):
        return True
    return False


rule = Rule(code=CODE, check=_check, requires_manifest=False)
