"""Manifest loader + id→macro-name transform.

The manifest is scitexlintr's published contract. Schema (every key optional):

    {
      "numbers": [
        {"id": "...", "value": ...,
         "label_canonical": "...",            (optional)
         "label_aliases_forbidden": [...]}    (optional)
      ],
      "figures": [
        {"id": "...", "path": "...", "sha256": "..."}
      ],
      "terms": [
        {"id": "...", "expansion": "...",
         "overloaded_warning": "..."}          (optional)
      ]
    }

Extra fields are ignored — the schema is tolerant of supersets (mycelium's
``.manifest.json`` carries `provenance`, `appears_in_sections`, etc.).

The id→macro-name transform is deterministic:

    1. Strip any namespace prefix — everything up to and including the last
       ``.``, ``:``, or ``/``.  ``diff-expr.n_samples`` → ``n_samples``.
       ``diff-expr:weird_ns_n_replicates`` → ``weird_ns_n_replicates``.
    2. Split the local key on ``_``.
    3. For each segment:
       * all-digit segment: map each digit to its English word
         (``0`` → ``Zero``, ``5`` → ``Five``); concatenate.
         ``05`` → ``ZeroFive``.
       * all-letter segment of length ≤ 3: uppercase
         (``fdr`` → ``FDR``, ``n`` → ``N``, ``de`` → ``DE``).
       * otherwise: title-case (``samples`` → ``Samples``).
    4. Concatenate all segments.

So ``fdr_threshold`` → ``FDRThreshold`` and
``n_de_genes_fdr_0_05`` → ``NDEGenesFDRZeroZeroFive``.

The macro names themselves are emitted by upstream tooling (e.g., mycelium's
``render_report_values_tex``); scitexlintr only needs to predict the same
name so it can match snapshots against the manifest.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


_DIGIT_WORDS = {
    "0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four",
    "5": "Five", "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine",
}

_NAMESPACE_SPLIT_RE = re.compile(r"[.:/]")


@dataclass(frozen=True)
class NumberEntry:
    id: str
    value: object  # int | float | str
    macro_name: str  # without leading backslash, e.g., "NSamples"
    label_canonical: str | None = None
    label_aliases_forbidden: tuple[str, ...] = ()

    @property
    def value_repr(self) -> str:
        """How this value would appear if the macro expanded directly into prose.

        Floats are rendered without trailing zeros and without scientific
        notation for the common case; strings pass through as-is.
        """
        v = self.value
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float):
            return _format_float(v)
        return str(v)


@dataclass(frozen=True)
class FigureEntry:
    id: str
    path: str
    sha256: str | None = None


@dataclass(frozen=True)
class TermEntry:
    id: str
    expansion: str
    overloaded_warning: str | None = None


@dataclass(frozen=True)
class Manifest:
    numbers: tuple[NumberEntry, ...] = ()
    figures: tuple[FigureEntry, ...] = ()
    terms: tuple[TermEntry, ...] = ()
    by_macro: dict[str, NumberEntry] = field(default_factory=dict)
    by_figure_path: dict[str, FigureEntry] = field(default_factory=dict)


def load_manifest(path: str | Path) -> Manifest:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_manifest(raw)


def parse_manifest(raw: dict) -> Manifest:
    numbers: list[NumberEntry] = []
    for entry in raw.get("numbers", []) or []:
        nid = entry.get("id")
        if not nid:
            continue
        macro = id_to_macro_name(nid)
        if not macro:
            continue
        numbers.append(
            NumberEntry(
                id=nid,
                value=entry.get("value"),
                macro_name=macro,
                label_canonical=entry.get("label_canonical"),
                label_aliases_forbidden=tuple(entry.get("label_aliases_forbidden") or []),
            )
        )

    figures: list[FigureEntry] = []
    for entry in raw.get("figures", []) or []:
        path = entry.get("path")
        if not path:
            continue
        figures.append(
            FigureEntry(
                id=entry.get("id", path),
                path=path,
                sha256=entry.get("sha256"),
            )
        )

    terms: list[TermEntry] = []
    for entry in raw.get("terms", []) or []:
        tid = entry.get("id")
        expansion = entry.get("expansion")
        if not tid or not expansion:
            continue
        terms.append(
            TermEntry(
                id=tid,
                expansion=expansion,
                overloaded_warning=entry.get("overloaded_warning"),
            )
        )

    by_macro = {n.macro_name: n for n in numbers}
    by_figure_path = {f.path: f for f in figures}

    return Manifest(
        numbers=tuple(numbers),
        figures=tuple(figures),
        terms=tuple(terms),
        by_macro=by_macro,
        by_figure_path=by_figure_path,
    )


def id_to_macro_name(manifest_id: str) -> str:
    """Apply the documented id → macro-name transform.

    Returns the macro name WITHOUT the leading backslash. Returns an empty
    string if the id can't yield a valid identifier (e.g., empty after
    stripping the namespace prefix).
    """
    # Strip namespace. Take the segment after the last namespace separator.
    parts = _NAMESPACE_SPLIT_RE.split(manifest_id)
    local = parts[-1] if parts else manifest_id
    if not local:
        return ""

    out_segments: list[str] = []
    for segment in local.split("_"):
        if not segment:
            continue
        if segment.isdigit():
            out_segments.append("".join(_DIGIT_WORDS[d] for d in segment))
        elif segment.isalpha() and len(segment) <= 3:
            out_segments.append(segment.upper())
        else:
            # Mixed or long letter segment — title-case it.
            out_segments.append(segment[0].upper() + segment[1:].lower())

    return "".join(out_segments)


def _format_float(v: float) -> str:
    # Avoid trailing zeros from a naive str() while keeping precision the
    # author likely wrote. ``0.05`` stays ``0.05``; ``0.10`` stays ``0.1``.
    # Python's ``repr`` already does the shortest-round-trip dance.
    return repr(v)


def values_equal_as_snapshot(value: object, snapshot: str) -> bool:
    """Return True iff ``snapshot`` represents the same value as ``value``.

    The match is forgiving:
      * Whitespace is stripped.
      * String values must match exactly (after strip).
      * Numeric values match if either the formatted repr matches OR both
        sides parse to floats whose magnitudes agree to 1e-12 relative
        tolerance.
      * Comma-grouping (``15,122``) is preserved when present on both sides
        but is also tolerated as equivalent to ``15122`` numerically.
    """
    snap = snapshot.strip()
    if isinstance(value, str):
        v = value.strip()
        if snap == v:
            return True
        # Numeric fallback: if BOTH the snapshot and the string-typed
        # manifest value parse as floats, compare numerically. This
        # handles emitters that JSON-encode every value as a string
        # (``"0.0500"`` vs ``0.05`` in prose).
        try:
            snap_f = float(snap.replace(",", ""))
            v_f = float(v.replace(",", ""))
        except ValueError:
            return False
        if v_f == 0.0:
            return abs(snap_f) < 1e-12
        return abs(snap_f - v_f) / abs(v_f) < 1e-12
    if isinstance(value, bool):
        return snap.lower() == ("true" if value else "false")
    if isinstance(value, (int, float)):
        # Try string match against canonical repr.
        if snap == _format_value(value):
            return True
        # Then numeric comparison, stripping commas.
        try:
            snap_f = float(snap.replace(",", ""))
        except ValueError:
            return False
        if isinstance(value, int):
            return snap_f == float(value)
        if value == 0.0:
            return abs(snap_f) < 1e-12
        return abs(snap_f - value) / abs(value) < 1e-12
    return False


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_float(value)
    return str(value)
