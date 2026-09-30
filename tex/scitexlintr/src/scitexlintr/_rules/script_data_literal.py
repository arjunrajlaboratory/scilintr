"""script-data-literal — numeric data typed into a report script.

Interactive figures must draw from registered, fingerprinted data blocks
(``unfingerprinted-data``). A script that carries its own numeric arrays —
``draw([0.1, 0.2, 0.35, 0.5, 0.8, 1.3])`` — sidesteps that check, so any
array literal of six or more numbers in a report script (other than the
shared ``sci-report-runtime`` block) is flagged. Short arrays such as
margins or tick steps stay below the threshold.

HTML only. Warning: legitimate constants exist; waive them with a reason.
"""

from __future__ import annotations

import re

from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "script-data-literal"
MIN_NUMBERS = 6
_ARRAY_RE = re.compile(r"\[([^\[\]]*)\]")
_NUMBER_ITEM_RE = re.compile(r"^\s*[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?\s*$")


def _check(doc, manifest: Manifest | None) -> list[Finding]:
    if getattr(doc, "fmt", "tex") != "html":
        return []
    findings: list[Finding] = []
    for script in doc.scripts:
        if script.runtime:
            continue
        for m in _ARRAY_RE.finditer(script.text):
            items = m.group(1).split(",")
            if len(items) >= MIN_NUMBERS and all(_NUMBER_ITEM_RE.match(i) for i in items):
                line, col = doc.lookup(script.body_start + m.start())
                findings.append(
                    Finding(
                        rule=CODE, line=line, col=col, severity="warning",
                        message=(f"array of {len(items)} numbers in a report script; draw interactive "
                                 "figures from a registered data-sci-data block instead"),
                    )
                )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=False)
