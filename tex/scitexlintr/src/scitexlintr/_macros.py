r"""Macros a TeX report defines itself — in the file, or in files it
``\input``\ s / ``\include``\ s.

``unknown-value-id`` flags a ``\SciVal{\Macro}`` whose macro no manifest
entry generates, because ``pdflatex`` stops on it. A macro the report defines
by hand compiles, so it is not unknown. Definitions are found by pattern,
not by running TeX: the common definers (``\newcommand`` and its LaTeX3 /
etoolbox / xargs relatives, ``\def`` and friends, ``\let``, ``\csdef``,
``\csname…\endcsname``).
"""

from __future__ import annotations

import re
from pathlib import Path

from scitexlintr._parser import strip_comments

_NAME = r"([A-Za-z@]+)"
_DEFINITION_RE = re.compile(
    # \newcommand, \renewcommand, \providecommand, \DeclareRobustCommand,
    # \NewDocumentCommand, \NewExpandableDocumentCommand, \newrobustcmd,
    # \newcommandx, \NewCommandCopy, \DeclareMathOperator — then \Name or {\Name}
    r"\\(?:[A-Za-z]*(?:[Cc]ommand|cmd)x?|NewCommandCopy|DeclareMathOperator)\*?\s*\{?\s*\\(?!csname\b)" + _NAME
    # \def \edef \gdef \xdef \let
    + r"|\\(?:[egx]?def|let)\s*\\" + _NAME
    # \csdef{Name}, \csgdef{Name}, …
    + r"|\\cs[egx]?def\s*\{\s*" + _NAME + r"\s*\}"
    # \expandafter\newcommand\csname Name\endcsname
    + r"|\\csname\s*" + _NAME + r"\s*\\endcsname"
)

_INCLUDE_RE = re.compile(r"\\(?:input|include|subfile)\s*\{\s*([^{}]+?)\s*\}")

_MAX_DEPTH = 10


def defined_macros(text: str) -> set[str]:
    """Macro names ``text`` (comments already stripped) defines."""
    return {next(g for g in m.groups() if g) for m in _DEFINITION_RE.finditer(text)}


def _resolve(target: str, base: Path) -> Path | None:
    for cand in (base / target, base / f"{target}.tex"):
        if cand.is_file():
            return cand
    return None


def defined_macros_in_file(path: Path, _seen: set[Path] | None = None, _depth: int = 0) -> set[str]:
    """Macros ``path`` defines, following ``\\input`` / ``\\include`` /
    ``\\subfile`` relative to the including file's directory. Unreadable or
    missing inputs contribute nothing."""
    seen = _seen if _seen is not None else set()
    try:
        real = path.resolve()
        if real in seen or _depth > _MAX_DEPTH:
            return set()
        seen.add(real)
        text = strip_comments(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return set()
    found = defined_macros(text)
    for m in _INCLUDE_RE.finditer(text):
        child = _resolve(m.group(1), path.parent)
        if child is not None:
            found |= defined_macros_in_file(child, seen, _depth + 1)
    return found
