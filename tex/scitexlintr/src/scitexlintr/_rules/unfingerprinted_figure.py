"""unfingerprinted-figure — \\includegraphics with a path the manifest doesn't know.

We don't (yet) verify the SHA — that requires file access and is a
``--strict`` feature. The path-membership check alone catches the common
failure: a figure regenerated under a different name, or a one-off plot
shipped without being registered.
"""

from __future__ import annotations

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "unfingerprinted-figure"


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    findings: list[Finding] = []
    for call in doc.calls("includegraphics"):
        if not call.args:
            continue
        path = call.args[-1].text.strip()
        if not path:
            continue
        if path in manifest.by_figure_path:
            continue
        line, col = doc.lookup(call.name_start)
        findings.append(
            Finding(
                rule=CODE,
                line=line,
                col=col,
                message=(
                    f"figure path {path!r} not registered in manifest — "
                    f"add to figures[*] with a sha256"
                ),
                severity="error",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=True)
