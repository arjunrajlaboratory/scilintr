"""Per-file preprocessed view of a TeX source — built once, queried by every rule."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from scitexlintr._parser import (
    MacroCall,
    build_prose_mask,
    find_body_range,
    find_macro_calls,
    line_col_lookup,
    strip_comments,
)


@dataclass
class TexDoc:
    filename: str
    source: str
    stripped: str
    body_start: int
    body_end: int
    macro_calls: tuple[MacroCall, ...]
    prose_mask: bytearray
    lookup: Callable[[int], tuple[int, int]]
    fmt: str = "tex"

    # Cached views (populated lazily by rules that need them).
    _calls_by_name: dict[str, tuple[MacroCall, ...]] | None = field(default=None, repr=False)

    def calls(self, name: str) -> tuple[MacroCall, ...]:
        if self._calls_by_name is None:
            grouped: dict[str, list[MacroCall]] = {}
            for c in self.macro_calls:
                grouped.setdefault(c.name, []).append(c)
            self._calls_by_name = {k: tuple(v) for k, v in grouped.items()}
        return self._calls_by_name.get(name, ())

    def in_prose(self, offset: int) -> bool:
        if 0 <= offset < len(self.prose_mask):
            return bool(self.prose_mask[offset])
        return False

    def wrap_hint(self, entry, label: str) -> str:
        """The wrapper spelling a rule suggests for a raw manifest value."""
        wrapper = "SciText" if isinstance(entry.value, str) else "SciVal"
        return f"\\{wrapper}{{\\{entry.macro_name}}}{{{label}}}"

    def offset_in_wrapper_first_arg(self, offset: int) -> bool:
        """True if ``offset`` lies inside the first argument of a wrapper macro
        (``\\SciVal`` / ``\\SciText``). Used by bare-generated-macro to allow
        ``\\NSamples`` when it appears as the first arg of a wrapper."""
        for c in self.macro_calls:
            if c.name in ("SciVal", "SciText") and c.args:
                a0 = c.args[0]
                if a0.start <= offset < a0.end:
                    return True
        return False


def prepare(source: str, filename: str) -> TexDoc:
    stripped = strip_comments(source)
    body_start, body_end = find_body_range(stripped)
    macro_calls = tuple(find_macro_calls(stripped, names=None, scope=(0, len(stripped))))
    prose_mask = build_prose_mask(stripped, body_start, body_end)
    return TexDoc(
        filename=filename,
        source=source,
        stripped=stripped,
        body_start=body_start,
        body_end=body_end,
        macro_calls=macro_calls,
        prose_mask=prose_mask,
        lookup=line_col_lookup(source),
    )


# ---------------------------------------------------------------------------
# Helper: collapse arg text whose body is a single ``\macro`` reference.
# ---------------------------------------------------------------------------

def phrase_pattern(phrase: str, fmt: str = "tex", flags: int = 0, boundary: str = r"\w") -> "re.Pattern[str]":
    """A regex for ``phrase`` as a reader sees it: words separated by any run
    of whitespace — a line break in the source, the spaces an HTML tag or
    ``&nbsp;`` leaves in the prose view (``treated <em>versus</em> control``),
    or a TeX tie (``treated~versus``). Every rule that matches a phrase uses
    this one definition, so none of them compares exact single spaces against
    text whose whitespace varies.

    ``boundary`` is the character class that must not touch the phrase's ends
    (only enforced where the phrase itself starts or ends with one).
    """
    words = phrase.split()
    if not words:
        return re.compile(r"(?!)")
    sep = r"(?:\s|~)+" if fmt == "tex" else r"\s+"
    body = sep.join(re.escape(w) for w in words)
    lead = rf"(?<!{boundary})" if re.match(boundary, words[0][0]) else ""
    trail = rf"(?!{boundary})" if re.match(boundary, words[-1][-1]) else ""
    return re.compile(lead + body + trail, flags)


def skip_inline_space(text: str, i: int) -> int:
    """Offset of the first character at or after ``i`` that is not a space or tab."""
    while i < len(text) and text[i] in " \t":
        i += 1
    return i


_TEX_UNIT_SPACE_RE = re.compile(r"(?:[ \t~]|\\[,;: ]|\\thinspace\b\s*)*")


def skip_unit_space(text: str, i: int, fmt: str = "tex") -> int:
    """Offset past the spacing that may sit between a number and its unit:
    spaces and tabs, plus in TeX ``~``, ``\\,``, ``\\;``, ``\\:``, ``\\ ``
    and ``\\thinspace`` (``97\\,\\%``)."""
    if fmt == "html":
        return skip_inline_space(text, i)
    return _TEX_UNIT_SPACE_RE.match(text, i).end()


_MACRO_REF_RE = re.compile(r"^\s*\\([A-Za-z@]+)\s*$")


def extract_macro_ref(arg_text: str) -> str | None:
    """If ``arg_text`` is exactly ``\\Name`` (with optional surrounding
    whitespace), return ``"Name"``. Otherwise ``None``."""
    m = _MACRO_REF_RE.match(arg_text)
    return m.group(1) if m else None
