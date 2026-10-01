"""unknown-value-id — a value wrapper naming an id the manifest lacks.

HTML: ``<span data-sci-val="n_smaples">48</span>`` renders its literal text and
would otherwise escape every check. Resolution matches
``Manifest.resolve_number`` (exact id, then the namespace-stripped id→macro
transform).

TeX: ``\\SciVal{\\NSmaples}{48}`` names a macro no manifest entry generates —
typically left behind after an entry was un-registered. Every other rule
skips it, and ``pdflatex`` then dies on an undefined control sequence.
Macros the document defines itself (``\\newcommand`` / ``\\def``) compile and
are not flagged; a macro from an ``\\input`` file is not visible here.
"""

from __future__ import annotations

import re

from scitexlintr._doc import extract_macro_ref
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._parser import WRAPPER_MACROS
from scitexlintr._rules._base import Rule

CODE = "unknown-value-id"


def _check(doc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    if doc.fmt != "html":
        return _check_tex(doc, manifest)
    findings: list[Finding] = []
    for w in doc.wrappers:
        if manifest.resolve_number(w.key) is not None:
            continue
        line, col = doc.lookup(w.start)
        attr = "data-sci-val" if w.kind == "val" else "data-sci-text"
        findings.append(
            Finding(
                rule=CODE,
                line=line,
                col=col,
                message=f"{attr}={w.key!r} does not name a manifest numbers[*] id",
                severity="error",
            )
        )
    return findings


# `\newcommand{\Foo}`, `\renewcommand*\Foo`, `\providecommand`, `\def\Foo`, …
_DEFINITION_RE = re.compile(
    r"\\(?:(?:re|provide)?newcommand|providecommand|DeclareRobustCommand"
    r"|(?:New|Renew|Provide|Declare)DocumentCommand|NewCommandCopy)\*?\s*\{?\s*\\([A-Za-z@]+)"
    r"|\\(?:[egx]?def|let)\s*\\([A-Za-z@]+)"
)


def _document_defined_macros(text: str) -> set[str]:
    """Macros the document defines itself. They compile, so they are not
    unknown — though their snapshots stay unchecked (no manifest entry)."""
    return {m.group(1) or m.group(2) for m in _DEFINITION_RE.finditer(text)}


def _check_tex(doc, manifest: Manifest) -> list[Finding]:
    findings: list[Finding] = []
    local = _document_defined_macros(doc.stripped)
    for wrapper_name in sorted(WRAPPER_MACROS):
        for call in doc.calls(wrapper_name):
            if not call.args:
                continue
            macro = extract_macro_ref(call.args[0].text)
            if macro is None or macro in manifest.by_macro or macro in local:
                continue
            line, col = doc.lookup(call.args[0].start)
            findings.append(
                Finding(
                    rule=CODE,
                    line=line,
                    col=col,
                    message=(
                        f"\\{wrapper_name}{{\\{macro}}} names a macro no manifest numbers[*] "
                        "entry generates — its snapshot is unchecked, and pdflatex stops on an "
                        "undefined control sequence unless something else defines it"
                    ),
                    severity="error",
                )
            )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=True)
