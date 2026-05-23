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
        # Skip structural-macro args (\\label{}, \\ref{}, \\cite{}, \\input{},
        # etc.) — the prose mask already excludes those regions for every
        # other numeric rule; we mirror that here. The macro NAME itself is
        # always non-prose in the mask (the backslash byte is zeroed), so we
        # probe the byte immediately AFTER the name.
        probe = m.end()
        if probe < len(doc.prose_mask) and not doc.in_prose(probe):
            # The macro is in a non-prose region. The byte after the name
            # is also non-prose iff we're inside a structural arg; if we're
            # in normal prose, the byte after the name is the next prose
            # char (a space, punctuation, or a brace beginning a normal
            # argument group). Use the surrounding context to be sure:
            # check that the macro's NAME offset is inside a structural arg
            # by looking up the enclosing macro call.
            if _is_inside_structural_arg(doc, offset):
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


def _is_inside_structural_arg(doc, offset: int) -> bool:
    """True if ``offset`` lies inside any argument of a structural macro.

    We use the same STRUCTURAL_ARG_MACROS set the prose mask uses, so
    behavior matches every other rule: a generated macro buried inside
    ``\\label{...}`` / ``\\ref{...}`` / ``\\cite{...}`` is non-prose and
    must not fire bare-generated-macro.
    """
    from scitexlintr._parser import STRUCTURAL_ARG_MACROS
    for call in doc.macro_calls:
        if call.name not in STRUCTURAL_ARG_MACROS:
            continue
        for arg in call.args:
            if arg.start <= offset < arg.end:
                return True
        for opt in call.optional_args:
            if opt.start <= offset < opt.end:
                return True
    return False


rule = Rule(code=CODE, check=_check, requires_manifest=True)
