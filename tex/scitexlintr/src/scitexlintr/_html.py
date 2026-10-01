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
  ``p &lt; 0.05`` as ``p <    0.05``. A reference contributes the character
  it renders, so ``&#8211;`` adds a dash (never the digits of its code) and
  ``&#49;`` adds the digit 1.

Non-prose regions: ``<head>``, ``<script>``, ``<style>``, ``<code>``,
``<pre>``, ``<kbd>``, ``<samp>``, ``<math>``, ``<template>``,
``<textarea>``, ``<noscript>``; the content of value wrappers
(``data-sci-val`` / ``data-sci-text``, checked by snapshot-mismatch
instead); ``data-sci-live`` readouts that script rewrites at runtime; ``<time>``
elements (dates in bylines and citations are not claims); and the
fingerprinted regions — the text between a registered figure's
``<!-- sci-media -->`` markers and between a registered table's
``<!-- sci-rows -->`` markers. The exemption is exactly the hashed span:
captions, notes, and anything else inside the ``<figure>`` or ``<table>``
are prose.

The scanner also records the exact source text of each fingerprinted
region — figure media between ``<!-- sci-media -->`` markers, a data
block's payload, a registered table's rows between ``<!-- sci-rows -->``
markers — so the rules can recompute ``data-content-sha256`` and catch a
hand edit to inlined content.

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
    "template", "textarea", "noscript", "title", "time",
})
VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})
# Every element that embeds an image, media, or another document. Outside a
# registered figure's media region, each one is an unregistered figure.
EMBED_TAGS = frozenset({
    "img", "image", "source", "video", "audio", "iframe", "object", "embed", "canvas",
})
_EMBED_SRC_ATTRS = ("src", "data", "href", "xlink:href", "srcset", "poster")
JS_TYPES = ("", "text/javascript", "module", "application/javascript")


@dataclass(frozen=True)
class Wrapper:
    kind: str                 # "val" | "text"
    key: str                  # manifest id as written in the attribute
    precision: str | None     # data-precision attribute, if any
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
    content_sha256: str | None = None   # data-content-sha256
    media: str | None = None            # source text between sci-media markers


@dataclass(frozen=True)
class TableInfo:
    start: int
    data_id: str              # data[*] id, or worked_examples[*] id when kind == "worked"
    sha256: str | None
    content_sha256: str | None
    rows: str | None          # source text between sci-rows markers
    kind: str = "data"        # "data" (data-sci-table) | "worked" (data-sci-worked)


@dataclass(frozen=True)
class MediaRef:
    start: int
    tag: str
    src: str
    in_registered_figure: bool   # inside a registered figure's sci-media region
    in_interactive_figure: bool = False


@dataclass(frozen=True)
class DataBlock:
    start: int
    data_id: str
    sha256: str | None
    content_sha256: str | None = None
    payload: str = ""
    type: str = ""


@dataclass(frozen=True)
class UnregisteredData:
    """A non-JavaScript ``<script>`` (JSON, text, …) that is not a registered
    data block: data a custom figure could read without any fingerprint."""
    start: int
    type: str


@dataclass(frozen=True)
class ScriptInfo:
    start: int
    body_start: int
    text: str
    runtime: bool             # id="sci-report-runtime"


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
    tables: tuple[TableInfo, ...] = ()
    scripts: tuple[ScriptInfo, ...] = ()
    unregistered_data: tuple[UnregisteredData, ...] = ()
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
        self.tables: list[TableInfo] = []
        self.scripts: list[ScriptInfo] = []
        self.unregistered_data: list[UnregisteredData] = []
        # The fingerprinted region currently open ("sci-media" / "sci-rows"),
        # entered and left at the marker comments. The prose exemption and
        # "registered media" status cover exactly this region — the same span
        # data-content-sha256 hashes — never the whole element.
        self.region: str | None = None

    # -- position helpers -------------------------------------------------

    def _offset(self) -> int:
        line, col = self.getpos()
        return self._line_starts[line - 1] + col

    def _in_nonprose(self) -> bool:
        return self.region is not None or (bool(self.stack) and self.stack[-1].nonprose)

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

        if tag in EMBED_TAGS:
            src = next((attrs[k] or "" for k in _EMBED_SRC_ATTRS if attrs.get(k)), "")
            fig = self._ancestor(lambda e: e.tag == "figure")
            interactive = fig is not None and "data-sci-interactive" in fig.attrs
            self.media.append(MediaRef(start, tag, src, self.region == "sci-media", interactive))

        if tag == "script" and attrs.get("data-sci-data"):
            fig = self._ancestor(lambda e: e.tag == "figure")
            if fig is not None:
                fig.data_ids.append(attrs["data-sci-data"] or "")

        if self_closing or tag in VOID_TAGS:
            return

        parent_nonprose = self._in_nonprose()
        nonprose = parent_nonprose or tag in NONPROSE_TAGS
        if "data-sci-val" in attrs or "data-sci-text" in attrs or "data-sci-live" in attrs:
            nonprose = True
        self.stack.append(_Elem(tag, attrs, start, open_end, nonprose))

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
                Wrapper(kind, key, attrs.get("data-precision"), el.start, el.open_end, close_start,
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
                    content_sha256=attrs.get("data-content-sha256"),
                    media=self._between_markers("sci-media", el.open_end, close_start),
                )
            )
        if el.tag == "table" and (attrs.get("data-sci-table") or attrs.get("data-sci-worked")):
            worked = bool(attrs.get("data-sci-worked"))
            self.tables.append(
                TableInfo(
                    start=el.start,
                    data_id=(attrs.get("data-sci-worked") if worked else attrs.get("data-sci-table")) or "",
                    sha256=attrs.get("data-sha256"),
                    content_sha256=attrs.get("data-content-sha256"),
                    rows=self._between_markers("sci-rows", el.open_end, close_start),
                    kind="worked" if worked else "data",
                )
            )
        if el.tag == "script":
            body = self.source[el.open_end:close_start]
            script_type = (attrs.get("type") or "").strip().lower()
            if attrs.get("data-sci-data"):
                self.data_blocks.append(
                    DataBlock(el.start, attrs["data-sci-data"] or "", attrs.get("data-sha256"),
                              attrs.get("data-content-sha256"), body, script_type)
                )
            elif script_type not in JS_TYPES:
                if body.strip():
                    self.unregistered_data.append(UnregisteredData(el.start, script_type))
            elif "src" not in attrs:
                # Only the first runtime block is the shared runtime; a second
                # one is report code wearing its id.
                is_runtime = attrs.get("id") == "sci-report-runtime" and not any(s.runtime for s in self.scripts)
                self.scripts.append(ScriptInfo(el.start, el.open_end, body, is_runtime))

    def _between_markers(self, name: str, lo: int, hi: int) -> str | None:
        """Source text between ``<!-- name -->`` and ``<!-- /name -->`` inside [lo, hi)."""
        opening = closing = None
        for c in self.comments:
            if c.start < lo or c.end > hi:
                continue
            label = c.text.strip()
            if label == name and opening is None:
                opening = c
            elif label == "/" + name and opening is not None:
                closing = c
                break
        if opening is None or closing is None:
            return None
        return self.source[opening.end:closing.start]

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
        label = data.strip()
        if label == "sci-media" and self._ancestor(lambda e: e.tag == "figure" and bool(e.attrs.get("data-sci-fig"))):
            self.region = "sci-media"
        elif label == "sci-rows" and self._ancestor(lambda e: e.tag == "table" and bool(e.attrs.get("data-sci-table") or e.attrs.get("data-sci-worked"))):
            self.region = "sci-rows"
        elif label in ("/sci-media", "/sci-rows") and self.region == label[1:]:
            self.region = None

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
        tables=tuple(scanner.tables),
        scripts=tuple(scanner.scripts),
        unregistered_data=tuple(scanner.unregistered_data),
    )
