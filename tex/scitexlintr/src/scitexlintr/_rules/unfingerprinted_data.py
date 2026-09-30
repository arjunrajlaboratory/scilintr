"""unfingerprinted-data — an interactive HTML figure whose data is not registered.

Sliders and animations redraw from data at runtime, so the numbers a reader
sees there never pass through the value wrappers. The only way to keep them
traceable is to fingerprint the data itself: every
``<script type="application/json" data-sci-data="id" data-sha256="…">``
block must name an id in the manifest's ``data[*]`` with a matching sha256,
and every ``<figure data-sci-interactive>`` must contain at least one such
block (a figure that draws from hand-typed arrays in script is exactly the
drift this rule exists to catch).

Each block also carries ``data-content-sha256``, the sha256 of the payload
exactly as inlined, so a hand edit to the embedded data is caught without
access to the source file. The same pair of hashes guards registered tables
(``<table data-sci-table="id">``), whose rows between ``<!-- sci-rows -->``
markers are generated from a ``data[*]`` file.

HTML only; TeX has no interactive figures.
"""

from __future__ import annotations

import hashlib

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

    def check(kind: str, start: int, data_id: str, sha: str | None, content_sha: str | None, content: str | None):
        entry = manifest.by_data_id.get(data_id)
        if entry is None:
            emit(start, f"{kind} id {data_id!r} not registered in manifest data[*]")
            return
        if entry.sha256 and (sha or "").lower() != entry.sha256.lower():
            got = (sha or "missing")[:12]
            emit(start, f"{kind} {data_id!r} data-sha256 {got} disagrees with manifest "
                        f"sha256 {entry.sha256[:12]}… — re-sync it")
            return
        if content is None:
            emit(start, f"{kind} {data_id!r} has no generated content markers; re-sync it")
            return
        actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if not content_sha:
            emit(start, f"{kind} {data_id!r} has no data-content-sha256; re-sync it")
        elif content_sha.lower() != actual:
            emit(start, f"{kind} {data_id!r} content was edited after sync (data-content-sha256 does not match); re-sync it")

    for block in doc.data_blocks:
        if block.type != "application/json":
            # The runtime reads only script[type="application/json"][data-sci-data];
            # any other type renders a blank figure (and a missing type runs the
            # payload as JavaScript).
            emit(block.start, f"data block {block.data_id!r} must be type=\"application/json\" "
                              f"(got {block.type or 'no type'}); the runtime reads only JSON blocks")
            continue
        check("data block", block.start, block.data_id, block.sha256, block.content_sha256, block.payload)
    for other in getattr(doc, "unregistered_data", ()):
        emit(other.start, f"<script type=\"{other.type}\"> holds data outside a registered data-sci-data "
                          "block; register it in manifest data[*] or remove it")
    for table in doc.tables:
        check("table", table.start, table.data_id, table.sha256, table.content_sha256, table.rows)

    for fig in doc.figures:
        if fig.interactive and not fig.data_ids:
            emit(
                fig.start,
                "interactive figure has no data-sci-data block — embed its data as "
                "registered JSON instead of literals in script",
            )
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=True)
