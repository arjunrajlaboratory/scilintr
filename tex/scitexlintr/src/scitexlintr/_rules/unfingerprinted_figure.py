"""unfingerprinted-figure — a figure the manifest does not vouch for.

TeX: ``\\includegraphics`` with a path not in ``figures[*]`` (the sha256 is
not checked in TeX — that needs file access). The path check catches the
common failure: a figure regenerated under a different name, or a one-off
plot shipped without being registered.

Path matching is forgiving in the same ways LaTeX is forgiving:

* leading ``./`` is stripped (LaTeX treats ``./foo`` and ``foo`` identically);
* the ``\\includegraphics{...}`` argument may omit the extension (LaTeX
  resolves it through ``\\DeclareGraphicsExtensions``), so we also try
  appending each known graphics extension to the tex-side path and
  matching against the manifest;
* conversely, if the manifest registered an extensionless path and the
  document spells out the extension, we strip the document's extension
  and re-check.

Anything more elaborate (multiple ``\\graphicspath`` roots, absolute path
resolution against the manifest's project root) is out of scope for v0.1.

HTML reports inline their figures, so a path alone cannot identify them.
The HTML contract is declarative instead — every ``<figure>`` says what it
is:

* ``<figure data-sci-fig="id" data-sha256="…">`` — a registered analysis
  figure. The id must be in ``figures[*]``, and when the manifest records a
  sha256 the attribute must equal it (a stale inline copy is drift). The
  media must sit between ``<!-- sci-media -->`` markers (the sync tool
  writes it there), and ``data-content-sha256`` must equal the sha256 of
  that text — ``data-sha256`` alone can be copied from the manifest onto
  any image, so the content hash is what ties the pixels to the file.
* ``<figure data-sci-interactive="name">`` — checked by
  ``unfingerprinted-data`` instead.
* ``<figure data-sci-diagram>`` — a hand-drawn schematic; its text is prose.

A ``<figure>`` declaring none of these is an error, and so is every
media-embedding element (``<img>``, SVG ``<image>``, ``<source>``,
``<video>``, ``<audio>``, ``<iframe>``, ``<object>``, ``<embed>``,
``<canvas>``) outside a registered figure's ``sci-media`` region — except an
``<img>`` / ``<image>`` whose path is in ``figures[*]``, and a ``<canvas>``
inside an interactive figure.
"""

from __future__ import annotations

import hashlib

from scitexlintr._doc import TexDoc
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest
from scitexlintr._rules._base import Rule

CODE = "unfingerprinted-figure"

# Extensions LaTeX's graphics package resolves by default. Order matches
# graphicx's typical search order.
_GRAPHICS_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".ps", ".svg")


def _normalize(path: str) -> str:
    p = path.strip()
    while p.startswith("./"):
        p = p[2:]
    return p


def _path_matches_manifest(tex_path: str, manifest: Manifest) -> bool:
    """Match a ``\\includegraphics`` path against a manifest entry.

    Forgiving in ONE direction: the tex may omit the extension and we'll
    try the known graphics extensions against extension-bearing manifest
    entries. We do NOT match in the other direction — an extensionless
    manifest entry is treated as a specific file (sha256 attached), not
    as a stem that swallows any tex-side extension.
    """
    normalized_index = {_normalize(k) for k in manifest.by_figure_path}
    tex = _normalize(tex_path)
    if tex in normalized_index:
        return True
    # Document omitted an extension that the manifest spelled out. Only
    # safe when the tex path has no extension itself.
    if "." not in tex.rsplit("/", 1)[-1]:
        for ext in _GRAPHICS_EXTENSIONS:
            if tex + ext in normalized_index:
                return True
    return False


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    if doc.fmt == "html":
        return _check_html(doc, manifest)
    findings: list[Finding] = []
    for call in doc.calls("includegraphics"):
        if not call.args:
            continue
        path = call.args[-1].text.strip()
        if not path:
            continue
        if _path_matches_manifest(path, manifest):
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


def _check_html(doc, manifest: Manifest) -> list[Finding]:
    findings: list[Finding] = []

    def emit(offset: int, message: str) -> None:
        line, col = doc.lookup(offset)
        findings.append(Finding(rule=CODE, line=line, col=col, message=message, severity="error"))

    for fig in doc.figures:
        if fig.fig_id:
            entry = manifest.by_figure_id.get(fig.fig_id)
            if entry is None:
                emit(fig.start, f"figure id {fig.fig_id!r} not registered in manifest figures[*]")
            elif entry.sha256 and not fig.sha256:
                emit(fig.start, f"figure {fig.fig_id!r} has no data-sha256; manifest sha256 is {entry.sha256[:12]}…")
            elif entry.sha256 and fig.sha256.lower() != entry.sha256.lower():
                emit(
                    fig.start,
                    f"figure {fig.fig_id!r} data-sha256 {fig.sha256[:12]}… disagrees with "
                    f"manifest sha256 {entry.sha256[:12]}… — the inlined copy is stale; re-sync it",
                )
            if entry is not None and fig.media is None:
                emit(fig.start, f"figure {fig.fig_id!r} has no <!-- sci-media --> markers; inline it with sync_html_report.py")
            elif entry is not None:
                actual = hashlib.sha256(fig.media.encode("utf-8")).hexdigest()
                if not fig.content_sha256:
                    emit(fig.start, f"figure {fig.fig_id!r} has inlined media but no data-content-sha256; re-sync it")
                elif fig.content_sha256.lower() != actual:
                    emit(fig.start, f"figure {fig.fig_id!r} media was edited after sync (data-content-sha256 does not match); re-sync it")
        elif not (fig.interactive or fig.diagram):
            emit(
                fig.start,
                "figure declares neither data-sci-fig, data-sci-interactive, nor "
                "data-sci-diagram — register it or mark it as a diagram",
            )

    for m in doc.media:
        if m.in_registered_figure or m.exempt:
            continue
        if m.tag == "canvas" and m.in_interactive_figure:
            continue  # a custom interactive kind draws here from registered data
        if m.tag in ("img", "image") and m.src and not m.src.startswith("data:") and _path_matches_manifest(m.src, manifest):
            continue
        shown = m.src if len(m.src) <= 60 else m.src[:57] + "..."
        emit(m.start, f"<{m.tag}> {shown!r} is outside a registered figure's sci-media region "
                      "and not in manifest figures[*]")
    return findings


rule = Rule(code=CODE, check=_check, requires_manifest=True)
