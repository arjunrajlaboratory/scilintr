"""unknown-value-id — a value wrapper naming an id the manifest lacks.

HTML: ``<span data-sci-val="n_smaples">48</span>`` renders its literal text and
would otherwise escape every check. Resolution matches
``Manifest.resolve_number`` (exact id, then the namespace-stripped id→macro
transform).

TeX: ``\\SciVal{\\NSmaples}{48}`` names a macro no manifest entry generates —
typically left behind after an entry was un-registered. Every other rule
skips it, and ``pdflatex`` then dies on an undefined control sequence.
Macros the report defines by hand compile and are not flagged: in the file
itself, in files it ``\\input``\\ s (``lint_file``), or in any file of the same
CLI run (see ``_macros``).
"""

from __future__ import annotations


from scitexlintr._doc import extract_macro_ref
from scitexlintr._finding import Finding
from scitexlintr._macros import defined_macros
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


def _check_tex(doc, manifest: Manifest) -> list[Finding]:
    findings: list[Finding] = []
    local = defined_macros(doc.stripped) | getattr(doc, "external_macros", frozenset())
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
