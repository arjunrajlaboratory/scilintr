"""unfingerprinted-data — an interactive HTML figure whose data is not registered.

Sliders and animations redraw from data at runtime, so the numbers a reader
sees there never pass through the value wrappers. The only way to keep them
traceable is to fingerprint the data itself: every
``<script type="application/json" data-sci-data="id" data-sha256="…">``
block must name an id in the manifest's ``data[*]`` with a matching sha256,
and every ``<figure data-sci-interactive>`` must contain at least one such
block (a figure that draws from hand-typed arrays in script is exactly the
drift this rule exists to catch).

HTML only; TeX has no interactive figures.
"""

from __future__ import annotations

from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "unfingerprinted-data"


def _check(doc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None or doc.fmt != "html":
        return []
    findings: list[Finding] = []

    def emit(offset: int, message: str) -> None:
        line, col = doc.lookup(offset)
        findings.append(Finding(rule=CODE, line=line, col=col, message=message, severity="error"))

    for block in doc.data_blocks:
        entry = manifest.by_data_id.get(block.data_id)
        if entry is None:
            emit(block.start, f"data block id {block.data_id!r} not registered in manifest data[*]")
        elif entry.sha256 and (block.sha256 or "").lower() != entry.sha256.lower():
            got = (block.sha256 or "missing")[:12]
            emit(
                block.start,
                f"data block {block.data_id!r} data-sha256 {got} disagrees with manifest "
                f"sha256 {entry.sha256[:12]}… — re-sync the embedded data",
            )

    for fig in doc.figures:
        if fig.interactive and not fig.data_ids:
            emit(
                fig.start,
                "interactive figure has no data-sci-data block — embed its data as "
                "registered JSON instead of literals in script",
            )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=True)
