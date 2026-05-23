"""unfingerprinted-figure — \\includegraphics with a path the manifest doesn't know.

We don't (yet) verify the SHA — that requires file access and is a
``--strict`` feature. The path-membership check alone catches the common
failure: a figure regenerated under a different name, or a one-off plot
shipped without being registered.

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
"""

from __future__ import annotations

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


rule = Rule(code=CODE, check=_check, requires_manifest=True)
