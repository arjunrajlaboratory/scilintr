"""raw-generated-value — literal manifest value used in prose without a wrapper.

If the manifest says ``n_de_genes = 317`` and prose contains the bare
substring ``317`` (outside any ``\\SciVal`` / ``\\SciText`` wrapper), fire.

Numeric values are matched by scanning numeric tokens and comparing them
**numerically** with the same comparator the ``snapshot-mismatch`` rule
uses (``values_equal_as_snapshot``). The detector and the comparator must
agree: a token like ``0.730`` matches a manifest value of ``0.73``
(trailing zero), ``15,122`` matches ``15122`` (comma grouping), and
``1e-8`` matches ``1e-08`` / ``0.00000001`` (notation / precision). An
exact-string match would miss those, and because such a token also "has a
manifest entry" it would slip past ``unsourced-numeric-token`` too —
landing in neither rule, silently un-checked. Token boundaries still hold,
so ``317`` does not match ``3175``. String values are matched verbatim —
short string values like ``"a"`` should not be added to manifests
(false-positive risk), but the linter itself doesn't enforce a minimum
length.
"""

from __future__ import annotations

import re

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest, values_equal_as_snapshot
from scitexlintr._rules._base import Rule

CODE = "raw-generated-value"


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    findings: list[Finding] = []
    # De-dup by (offset, manifest-id) so we don't report the same position
    # twice if two manifest entries share a value (e.g., n_control=24 and
    # n_treated=24 — we still want one finding per occurrence).
    seen_offsets: set[int] = set()

    for entry in manifest.numbers:
        if entry.value is None:
            continue
        for match_start, match_end, label in _find_value_matches(
            doc.stripped, entry.value
        ):
            if not doc.in_prose(match_start):
                continue
            if match_start in seen_offsets:
                continue
            seen_offsets.add(match_start)
            line, col = doc.lookup(match_start)
            findings.append(
                Finding(
                    rule=CODE,
                    line=line,
                    col=col,
                    message=(
                        f"raw value {label!r} appears in prose; wrap with "
                        f"\\SciVal{{\\{entry.macro_name}}}{{{label}}} "
                        f"(manifest id={entry.id})"
                    ),
                    severity="error",
                )
            )
    return findings


# A maximal numeric token: optional sign, an integer part (optionally
# comma-grouped), an optional fractional part, and an optional exponent.
# The surrounding ``(?<![\w.])`` / ``(?![\w.])`` guards keep tokens maximal
# so ``317`` is not matched inside ``3175`` or ``3.175``.
_NUMERIC_TOKEN_RE = re.compile(
    r"(?<![\w.])[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][+-]?\d+)?(?![\w.])"
)


def _find_value_matches(text: str, value: object):
    """Yield ``(start, end, label)`` for every occurrence of ``value`` in ``text``.

    Numeric values are matched by scanning numeric tokens and comparing
    numerically (see ``values_equal_as_snapshot``), so trailing-zero,
    comma-grouped, and scientific-notation variants all match. Strings are
    matched verbatim with case-sensitivity (a case-insensitive match would
    over-fire on common words).
    """
    if isinstance(value, str):
        if not value:
            return
        # Use a sliding find for verbatim matches.
        i = 0
        while True:
            j = text.find(value, i)
            if j < 0:
                return
            yield j, j + len(value), value
            i = j + len(value)
        return

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for m in _NUMERIC_TOKEN_RE.finditer(text):
            tok = m.group(0)
            if values_equal_as_snapshot(value, tok):
                yield m.start(), m.end(), tok


rule = Rule(code=CODE, check=_check, requires_manifest=True)
