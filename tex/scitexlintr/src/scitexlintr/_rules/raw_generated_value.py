"""raw-generated-value — literal manifest value used in prose without a wrapper.

If the manifest says ``n_de_genes = 317`` and prose contains the bare
substring ``317`` (outside any ``\\SciVal`` / ``\\SciText`` wrapper), fire.

Numeric values are matched with word boundaries so ``317`` doesn't match
``3175``. String values are matched verbatim — short string values like
``"a"`` should not be added to manifests (false-positive risk), but the
linter itself doesn't enforce a minimum length.
"""

from __future__ import annotations

import re

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
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


def _find_value_matches(text: str, value: object):
    """Yield ``(start, end, label)`` for every occurrence of ``value`` in ``text``.

    Numerics are matched with a regex anchored on word boundaries; strings
    are matched verbatim with case-sensitivity (case-insensitive match
    would over-fire on common words).
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
        # Build candidate strings:
        #   * canonical (str(int) or repr(float))
        #   * comma-grouped int form (15122 -> 15,122)
        #   * for floats that repr as scientific notation, also emit the
        #     unpadded form. ``repr(1e-8)`` is ``'1e-08'`` (zero-padded
        #     exponent), but prose conventionally writes ``1e-8``.
        canonicals: list[str] = []
        if isinstance(value, int):
            canonicals.append(str(value))
            if abs(value) >= 1000:
                canonicals.append(f"{value:,}")
        else:
            canonical = repr(value)
            canonicals.append(canonical)
            unpadded = _unpad_exponent(canonical)
            if unpadded != canonical:
                canonicals.append(unpadded)
        seen_strs: set[str] = set()
        for cand in canonicals:
            if cand in seen_strs:
                continue
            seen_strs.add(cand)
            pattern = re.compile(r"(?<![\w.])" + re.escape(cand) + r"(?![\w.])")
            for m in pattern.finditer(text):
                yield m.start(), m.end(), cand


_EXP_RE = re.compile(r"([eE])([+-]?)0*(\d+)")


def _unpad_exponent(s: str) -> str:
    """Remove leading zeros from the exponent of a scientific-notation literal.

    ``'1e-08'`` → ``'1e-8'``. ``'1e+10'`` → ``'1e+10'`` (no zero to strip).
    """
    return _EXP_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}", s)


rule = Rule(code=CODE, check=_check, requires_manifest=True)
