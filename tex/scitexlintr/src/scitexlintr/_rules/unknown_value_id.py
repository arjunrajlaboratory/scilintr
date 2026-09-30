"""unknown-value-id — an HTML value wrapper naming an id the manifest lacks.

In TeX an undefined ``\\Macro`` stops compilation, so a typo cannot reach
the PDF. HTML has no such backstop: ``<span data-sci-val="n_smaples">48</span>``
renders its literal text and would otherwise escape every check. Resolution
matches ``Manifest.resolve_number`` (exact id, then the namespace-stripped
id→macro transform).

HTML only.
"""

from __future__ import annotations

from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "unknown-value-id"


def _check(doc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None or doc.fmt != "html":
        return []
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


rule = Rule(code=CODE, check=_check, requires_manifest=True)
