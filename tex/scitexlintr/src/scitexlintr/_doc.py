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

_MACRO_REF_RE = re.compile(r"^\s*\\([A-Za-z@]+)\s*$")


def extract_macro_ref(arg_text: str) -> str | None:
    """If ``arg_text`` is exactly ``\\Name`` (with optional surrounding
    whitespace), return ``"Name"``. Otherwise ``None``."""
    m = _MACRO_REF_RE.match(arg_text)
    return m.group(1) if m else None
