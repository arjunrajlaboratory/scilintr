"""HTML frontend — builds the same per-file view the rules query for TeX.

The rules scan ``doc.stripped`` inside ``[body_start, body_end)`` and keep
only matches whose offset ``doc.in_prose``. For TeX, ``stripped`` is the
source with comments blanked. For HTML it is a same-length string that
holds **only prose text**: tags, attributes, comments, and every non-prose
element's content are replaced by spaces (newlines kept), so offsets and
line/column numbers still point into the original file.

Two consequences worth knowing:

* Words separated only by markup stay separate (``3<sup>2</sup>`` is two
  tokens), which is what a reader sees.
* Character references are decoded in place and padded with spaces:
  ``&lt;`` becomes ``<`` + three spaces, so the threshold rules see
  ``p &lt; 0.05`` as ``p <    0.05``. Numeric references (``&#8211;``)
  therefore never leak their digits into the numeric rules.

Non-prose regions: ``<head>``, ``<script>``, ``<style>``, ``<code>``,
``<pre>``, ``<kbd>``, ``<samp>``, ``<math>``, ``<template>``,
``<textarea>``, ``<noscript>``; the content of value wrappers
(``data-sci-val`` / ``data-sci-text``, checked by snapshot-mismatch
instead); ``data-sci-live`` readouts that script rewrites at runtime; and
everything inside a registered ``data-sci-fig`` figure except its
``<figcaption>`` (the media is fingerprinted; the caption is prose).

Stdlib ``html.parser`` only — no runtime dependencies.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable

from scitexlintr._parser import line_col_lookup

NONPROSE_TAGS = frozenset({
    "head", "script", "style", "code", "pre", "kbd", "samp", "math",
    "template", "textarea", "noscript", "title",
})
VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})
MEDIA_TAGS = frozenset({"img", "object", "embed"})


@dataclass(frozen=True)
class Wrapper:
    kind: str                 # "val" | "text"
    key: str                  # manifest id as written in the attribute
    start: int                # offset of the opening ``<span``
    inner_start: int          # offset just after the opening tag
    inner_end: int            # offset of the closing ``</span``
    text: str                 # rendered text, tags stripped, entities decoded
    has_markup: bool          # inner content contains tags or comments


@dataclass(frozen=True)
class FigureInfo:
    start: int
    fig_id: str | None        # data-sci-fig
    sha256: str | None        # data-sha256
    interactive: bool         # data-sci-interactive
    diagram: bool             # data-sci-diagram
    data_ids: tuple[str, ...]


@dataclass(frozen=True)
class MediaRef:
    start: int
    tag: str
    src: str
    in_registered_figure: bool


@dataclass(frozen=True)
class DataBlock:
    start: int
    data_id: str
    sha256: str | None


@dataclass(frozen=True)
class Comment:
    start: int
    end: int
    text: str


@dataclass
class HtmlDoc:
    filename: str
    source: str
    stripped: str
    body_start: int
    body_end: int
    prose_mask: bytearray
    lookup: Callable[[int], tuple[int, int]]
    wrappers: tuple[Wrapper, ...] = ()
    figures: tuple[FigureInfo, ...] = ()
    media: tuple[MediaRef, ...] = ()
    data_blocks: tuple[DataBlock, ...] = ()
    comments: tuple[Comment, ...] = ()
    fmt: str = "html"
    macro_calls: tuple = ()

    def calls(self, name: str) -> tuple:
        return ()

    def in_prose(self, offset: int) -> bool:
        if 0 <= offset < len(self.prose_mask):
            return bool(self.prose_mask[offset])
        return False

    def wrap_hint(self, entry, label: str) -> str:
        attr = "data-sci-text" if isinstance(entry.value, str) else "data-sci-val"
        return f'<span {attr}="{entry.id}">{label}</span>'


@dataclass
class _Elem:
    tag: str
    attrs: dict[str, str | None]
    start: int
    open_end: int
    nonprose: bool
    # Figure bookkeeping (only for <figure>).
    data_ids: list[str] = field(default_factory=list)


_WS_KEEP = "\n"


class _Scanner(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=False)
        self.source = source
        self.out = [c if c == _WS_KEEP else " " for c in source]
        self.mask = bytearray(len(source))
        self._line_starts = [0]
        for i, ch in enumerate(source):
            if ch == "\n":
                self._line_starts.append(i + 1)
        self.stack: list[_Elem] = []
        self.body_start: int | None = None
        self.body_end: int | None = None
        self.wrappers: list[Wrapper] = []
        self.figures: list[FigureInfo] = []
        self.media: list[MediaRef] = []
        self.data_blocks: list[DataBlock] = []
        self.comments: list[Comment] = []

    # -- position helpers -------------------------------------------------

    def _offset(self) -> int:
        line, col = self.getpos()
        return self._line_starts[line - 1] + col

    def _in_nonprose(self) -> bool:
        return bool(self.stack) and self.stack[-1].nonprose

    def _ancestor(self, predicate) -> _Elem | None:
        for el in reversed(self.stack):
            if predicate(el):
                return el
        return None

    # -- element handling -------------------------------------------------

    def handle_starttag(self, tag, attrs):
        self._start(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._start(tag, attrs, self_closing=True)

    def _start(self, tag: str, attr_list, *, self_closing: bool) -> None:
        start = self._offset()
        raw = self.get_starttag_text() or ""
        open_end = start + len(raw)
        attrs = {k: v for k, v in attr_list}

        if tag == "body" and self.body_start is None:
            self.body_start = open_end

        if tag in MEDIA_TAGS:
            src = attrs.get("src") or attrs.get("data") or ""
            fig = self._ancestor(lambda e: e.tag == "figure")
            registered = fig is not None and bool(fig.attrs.get("data-sci-fig"))
            self.media.append(MediaRef(start, tag, src, registered))

        if tag == "script" and attrs.get("data-sci-data"):
            self.data_blocks.append(
                DataBlock(start, attrs["data-sci-data"] or "", attrs.get("data-sha256"))
            )
            fig = self._ancestor(lambda e: e.tag == "figure")
            if fig is not None:
                fig.data_ids.append(attrs["data-sci-data"] or "")

        if self_closing or tag in VOID_TAGS:
            return

        parent_nonprose = self._in_nonprose()
        nonprose = parent_nonprose or tag in NONPROSE_TAGS
        if "data-sci-val" in attrs or "data-sci-text" in attrs or "data-sci-live" in attrs:
            nonprose = True
        if tag == "figure" and attrs.get("data-sci-fig"):
            nonprose = True
        if tag == "figcaption":
            fig = self._ancestor(lambda e: e.tag == "figure")
            if fig is not None and fig.attrs.get("data-sci-fig") and not self._blocked_above(fig):
                nonprose = False
        self.stack.append(_Elem(tag, attrs, start, open_end, nonprose))

    def _blocked_above(self, fig: _Elem) -> bool:
        """True if something *outside* ``fig`` already makes this region non-prose."""
        idx = self.stack.index(fig)
        return idx > 0 and self.stack[idx - 1].nonprose

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        pos = self._offset()
        if tag == "body" and self.body_end is None:
            self.body_end = pos
        # Pop to the nearest matching open element (tolerates implicit closes).
        for idx in range(len(self.stack) - 1, -1, -1):
            if self.stack[idx].tag == tag:
                popped = self.stack[idx:]
                del self.stack[idx:]
                # Finish implicitly closed descendants too (innermost first),
                # so an unclosed wrapper span is still recorded and checked.
                for el in reversed(popped):
                    self._finish(el, pos)
                return

    def _finish(self, el: _Elem, close_start: int) -> None:
        attrs = el.attrs
        kind = "val" if "data-sci-val" in attrs else "text" if "data-sci-text" in attrs else None
        if kind is not None:
            key = attrs.get("data-sci-val" if kind == "val" else "data-sci-text") or ""
            inner = self.source[el.open_end:close_start]
            has_markup = "<" in inner
            text = html.unescape(re.sub(r"<!--.*?-->|<[^>]*>", "", inner, flags=re.S))
            self.wrappers.append(
                Wrapper(kind, key, el.start, el.open_end, close_start,
                        " ".join(text.split()), has_markup)
            )
        if el.tag == "figure":
            self.figures.append(
                FigureInfo(
                    start=el.start,
                    fig_id=attrs.get("data-sci-fig"),
                    sha256=attrs.get("data-sha256"),
                    interactive="data-sci-interactive" in attrs,
                    diagram="data-sci-diagram" in attrs,
                    data_ids=tuple(el.data_ids),
                )
            )

    # -- text -------------------------------------------------------------

    def handle_data(self, data):
        if self._in_nonprose():
            return
        start = self._offset()
        for i, ch in enumerate(data):
            j = start + i
            if ch != "\n":
                self.out[j] = ch
            self.mask[j] = 1

    def _ref(self, raw_guess: str) -> None:
        start = self._offset()
        # Measure the raw reference in the source (the trailing ';' is optional).
        m = re.compile(r"&#?[A-Za-z0-9]+;?").match(self.source, start)
        end = m.end() if m else start + len(raw_guess)
        if self._in_nonprose():
            return
        decoded = html.unescape(self.source[start:end])
        ch = decoded[:1] if decoded else " "
        if ch.isspace() or ch == " ":
            ch = " "
        if ch.isdigit():
            ch = " "
        self.out[start] = ch
        for j in range(start, end):
            self.mask[j] = 1

    def handle_entityref(self, name):
        self._ref("&" + name + ";")

    def handle_charref(self, name):
        self._ref("&#" + name + ";")

    def handle_comment(self, data):
        start = self._offset()
        end = start + len(data) + len("<!---->")
        self.comments.append(Comment(start, end, data))

    def unknown_decl(self, data):  # <![CDATA[...]]> etc. — never prose
        return


def prepare_html(source: str, filename: str) -> HtmlDoc:
    scanner = _Scanner(source)
    scanner.feed(source)
    scanner.close()
    # Close anything left open so wrappers/figures at EOF are still recorded.
    while scanner.stack:
        el = scanner.stack.pop()
        scanner._finish(el, len(source))
    body_start = scanner.body_start if scanner.body_start is not None else 0
    body_end = scanner.body_end if scanner.body_end is not None else len(source)
    return HtmlDoc(
        filename=filename,
        source=source,
        stripped="".join(scanner.out),
        body_start=body_start,
        body_end=body_end,
        prose_mask=scanner.mask,
        lookup=line_col_lookup(source),
        wrappers=tuple(scanner.wrappers),
        figures=tuple(scanner.figures),
        media=tuple(scanner.media),
        data_blocks=tuple(scanner.data_blocks),
        comments=tuple(scanner.comments),
    )
