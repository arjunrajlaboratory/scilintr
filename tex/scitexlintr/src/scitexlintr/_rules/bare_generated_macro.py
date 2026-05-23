"""bare-generated-macro — a generated value macro used without a wrapper.

``\\NSamples`` rendered directly into prose IS fresh (the PDF shows the
current value) but it is UNREVIEWABLE — readers of the .tex source can't
see what value it expanded to. The wrapper convention exists precisely to
keep the source human-checkable; bypassing it defeats the whole point.
"""

from __future__ import annotations

import re

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "bare-generated-macro"


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    if not manifest.numbers:
        return []
    macro_names = {n.macro_name for n in manifest.numbers if n.macro_name}
    if not macro_names:
        return []

    findings: list[Finding] = []
    name_pattern = re.compile(
        r"\\(" + "|".join(re.escape(n) for n in macro_names) + r")(?![A-Za-z@])"
    )

    for m in name_pattern.finditer(doc.stripped, doc.body_start, doc.body_end):
        offset = m.start()
        # Allowed positions: inside the FIRST arg of a wrapper.
        if doc.offset_in_wrapper_first_arg(offset):
            continue
        name = m.group(1)
        line, col = doc.lookup(offset)
        findings.append(
            Finding(
                rule=CODE,
                line=line,
                col=col,
                message=(
                    f"generated macro \\{name} used without a \\SciVal/\\SciText "
                    f"wrapper — wrap as \\SciVal{{\\{name}}}{{<snapshot>}}"
                ),
                severity="warning",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=True)
