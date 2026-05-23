"""Threshold rules — share a single scanner.

* ``unwrapped-threshold`` (manifest-dependent, error): bare ``< 0.05`` in
  prose where ``0.05`` IS in the manifest. Should be wrapped.
* ``magic-tex-threshold`` (manifest-free, warning): bare ``< 0.01`` in
  prose where the value is NOT in the manifest. A magic number; promote
  to a named macro or waive.

Partitioning the threshold check this way keeps the two rules from both
firing on the same span.
"""

from __future__ import annotations

import re

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest, values_equal_as_snapshot
from scitexlintr._rules._base import Rule

UNWRAPPED_CODE = "unwrapped-threshold"
MAGIC_CODE = "magic-tex-threshold"

# A "threshold context" is a comparison operator (plain or LaTeX-spelled)
# followed by whitespace and a numeric literal.
_THRESHOLD_RE = re.compile(
    r"(?P<op>"
    r"<=|>=|<|>|"
    r"\\le(?:q)?(?![A-Za-z@])|"
    r"\\ge(?:q)?(?![A-Za-z@])|"
    r"\\ll(?![A-Za-z@])|"
    r"\\gg(?![A-Za-z@])"
    r")"
    r"\s*"
    r"(?P<num>\d+(?:\.\d+)?)"
)


def _iter_thresholds(doc: TexDoc):
    for m in _THRESHOLD_RE.finditer(doc.stripped, doc.body_start, doc.body_end):
        num_start = m.start("num")
        # Both the operator and the number must lie in prose. We test the
        # number position because the operator may be a backslash macro
        # (\le, \ge) whose backslash byte sits at a non-prose offset.
        if not doc.in_prose(num_start):
            continue
        yield m


def _check_unwrapped(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    findings: list[Finding] = []
    for m in _iter_thresholds(doc):
        num = m.group("num")
        entry = _matching_entry(manifest, num)
        if entry is None:
            continue
        line, col = doc.lookup(m.start("num"))
        findings.append(
            Finding(
                rule=UNWRAPPED_CODE,
                line=line,
                col=col,
                message=(
                    f"threshold {num} matches manifest id={entry.id}; "
                    f"wrap as \\SciVal{{\\{entry.macro_name}}}{{{num}}}"
                ),
                severity="error",
            )
        )
    return findings


def _check_magic(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    findings: list[Finding] = []
    for m in _iter_thresholds(doc):
        num = m.group("num")
        if manifest is not None and _matching_entry(manifest, num) is not None:
            # Caught by unwrapped-threshold instead.
            continue
        line, col = doc.lookup(m.start("num"))
        findings.append(
            Finding(
                rule=MAGIC_CODE,
                line=line,
                col=col,
                message=(
                    f"bare threshold {num} in prose without a named macro — "
                    f"register it in the manifest or add a waiver"
                ),
                severity="warning",
            )
        )
    return findings


def _matching_entry(manifest: Manifest, snap: str):
    for entry in manifest.numbers:
        if values_equal_as_snapshot(entry.value, snap):
            return entry
    return None


unwrapped_rule = Rule(code=UNWRAPPED_CODE, check=_check_unwrapped, requires_manifest=True)
magic_rule = Rule(code=MAGIC_CODE, check=_check_magic, requires_manifest=False)
