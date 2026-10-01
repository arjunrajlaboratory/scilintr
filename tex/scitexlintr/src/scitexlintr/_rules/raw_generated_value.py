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
so ``317`` does not match ``3175``. A percent-suffixed token
(``97.0\\%``) matching an integer value (usually a count) is reported at
warning severity — most often a coincidental collision.
String values are matched verbatim —
short string values like ``"a"`` should not be added to manifests
(false-positive risk), but the linter itself doesn't enforce a minimum
length.
"""

from __future__ import annotations

import re

from scitexlintr._display import derived_forms, normalize_number
from scitexlintr._doc import TexDoc, phrase_pattern, skip_unit_space
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
    clashes: dict[int, Finding] = {}

    for entry in manifest.numbers:
        if entry.value is None:
            continue
        for match_start, match_end, label, unit_clash in _find_value_matches(
            doc.stripped, entry.value, getattr(doc, "fmt", "tex")
        ):
            if not doc.in_prose(match_start):
                continue
            if match_start in seen_offsets:
                continue
            line, col = doc.lookup(match_start)
            if unit_clash:
                # ``97.0\%`` against an integer 97: usually a count colliding
                # with an unrelated percentage — but an integer can also be a
                # stored percent, so keep it visible at warning severity.
                # Deferred: an error on the same token (another entry, or a
                # rendered-form match below) must not be hidden behind it.
                clashes.setdefault(match_start, Finding(
                    rule=CODE, line=line, col=col, severity="warning",
                    message=(
                        f"percentage {label!r} equals integer manifest id={entry.id}; if it is "
                        f"that value, wrap with {doc.wrap_hint(entry, label)}, otherwise it is "
                        "likely a coincidental collision (waive it)"
                    ),
                ))
                continue
            seen_offsets.add(match_start)
            findings.append(
                Finding(
                    rule=CODE,
                    line=line,
                    col=col,
                    message=(
                        f"raw value {label!r} appears in prose; wrap with "
                        f"{doc.wrap_hint(entry, label)} (manifest id={entry.id})"
                    ),
                    severity="error",
                )
            )

    # Rendered forms of unit-derived values: 0.9535 with unit percent is
    # written "95.4%", so that literal is as raw as "0.9535" would be.
    by_number: dict[str, list] = {}
    for entry, number, suffix in derived_forms(manifest, getattr(doc, "fmt", "tex")):
        by_number.setdefault(normalize_number(number), []).append((entry, suffix, number))
    for m in _NUMERIC_TOKEN_RE.finditer(doc.stripped, doc.body_start, doc.body_end) if by_number else ():
        number = normalize_number(m.group(0))
        if number not in by_number or not doc.in_prose(m.start()) or m.start() in seen_offsets:
            continue
        after = skip_unit_space(doc.stripped, m.end(), getattr(doc, "fmt", "tex"))
        for entry, suffix, canonical in by_number[number]:
            if suffix and not doc.stripped.startswith(suffix, after):
                continue
            seen_offsets.add(m.start())
            label = m.group(0) + suffix
            # HTML spans show the rendered form; a TeX \SciVal snapshot is the stored value.
            snapshot = canonical + suffix if getattr(doc, "fmt", "tex") == "html" else entry.value_repr
            line, col = doc.lookup(m.start())
            findings.append(
                Finding(
                    rule=CODE, line=line, col=col, severity="error",
                    message=(f"raw value {label!r} is the rendered form of manifest id={entry.id}; "
                             f"wrap with {doc.wrap_hint(entry, snapshot)}"),
                )
            )
            break
    findings.extend(f for off, f in clashes.items() if off not in seen_offsets)
    return findings


# A maximal numeric token: optional sign, an integer part (optionally
# comma-grouped), an optional fractional part, and an optional exponent.
# The surrounding ``(?<![\w.])`` / ``(?![\w.])`` guards keep tokens maximal
# so ``317`` is not matched inside ``3175`` or ``3.175``.
_NUMERIC_TOKEN_RE = re.compile(
    r"(?<![\w.])[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][+-]?\d+)?(?![\w.])"
)


def _find_value_matches(text: str, value: object, fmt: str = "tex"):
    """Yield ``(start, end, label, unit_clash)`` for every occurrence of
    ``value`` in ``text``.

    Numeric values are matched by scanning numeric tokens and comparing
    numerically (see ``values_equal_as_snapshot``), so trailing-zero,
    comma-grouped, and scientific-notation variants all match. Strings are
    matched verbatim with case-sensitivity (a case-insensitive match would
    over-fire on common words). ``unit_clash`` marks a percent-suffixed token
    matching an integer value.
    """
    if isinstance(value, str):
        if not value:
            return
        # As a phrase, on word boundaries: the value "WT" is not raw inside
        # "WTF1" or "SWT", and "treated versus control" matches across a line
        # break or inline markup.
        for m in phrase_pattern(value, fmt).finditer(text):
            yield m.start(), m.end(), value, False
        return

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        percent = "%" if fmt == "html" else "\\%"
        for m in _NUMERIC_TOKEN_RE.finditer(text):
            tok = m.group(0)
            if not values_equal_as_snapshot(value, tok):
                continue
            unit_clash = isinstance(value, int) and text.startswith(
                percent, skip_unit_space(text, m.end(), fmt)
            )
            yield m.start(), m.end(), tok, unit_clash


rule = Rule(code=CODE, check=_check, requires_manifest=True)
