r"""Display formatting — how a manifest value is rendered in a report.

This is the single definition of the ``unit`` / ``precision`` / ``display``
contract. mycelium's ``render_report_values_tex`` applies the same rules
when it emits TeX macros; the HTML frontend uses them to check (and, with
``--write``, rewrite) the rendered text of every ``data-sci-val`` span.
Only the escaping differs between the two formats: TeX renders a percent
as ``97.8\\%``, HTML as ``97.8%``.

Selection order, identical in both formats:

1. ``unit`` set — derive the string from ``value``. ``unit="percent"`` turns
   the stored fraction ``0.978`` into ``97.8%`` at ``precision`` decimal
   places (default 1); ``unit="decimal"`` rounds ``7.47712`` to ``7.48`` at
   precision 2. Rounding is half-up on the value's decimal form, so
   ``0.9535`` at precision 1 is ``95.4%`` (binary-float formatting would give
   ``95.3%``).
2. a format-specific override — ``display`` (TeX source, verbatim) or
   ``display_html`` (HTML markup, verbatim: entities and inline tags such as
   ``10<sup>-4</sup>`` are allowed). An HTML wrapper is compared by rendered
   text, so ``3&times;`` and ``3×`` both satisfy ``display_html: "3&times;"``;
   ``--write`` inserts the markup as written. A ``display`` with no TeX
   markup is plain text and is used as-is in HTML; TeX markup means any of
   ``\\ $ { } ^ ~ %`` or the ligatures ``--``, ````\`\```` and ``''``, which
   need a ``display_html``.
3. neither — the natural form of the value.

HTML wrappers may narrow the precision of a derived value per span with
``data-precision="0"`` (a slide can show ``95%`` where the report shows
``95.4%``); it applies only to entries with a ``unit``.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext

SUPPORTED_UNITS = ("percent", "decimal")
_TEX_MARKUP_RE = re.compile(r"[\\${}^~%]|--|``|''")


def rendered_text(markup: str) -> str:
    """The text a browser shows for ``markup``: tags dropped, entities decoded,
    whitespace collapsed."""
    return " ".join(html.unescape(re.sub(r"<!--.*?-->|<[^>]*>", "", markup, flags=re.S)).split())


@dataclass(frozen=True)
class Expected:
    """What a wrapper's rendered text must be.

    ``text`` is the canonical rendering (used for ``--write``). ``exact``
    says whether the rendered text must equal ``text`` verbatim; when False
    (natural rendering of a bare number), any spelling that
    ``values_equal_as_snapshot`` accepts — ``15,122`` for ``15122`` — passes.
    ``problem`` is set instead when the entry cannot be rendered in this
    format at all.
    """

    text: str | None
    exact: bool
    problem: str | None = None
    markup: str | None = None   # HTML to insert on --write (None: escape ``text``)


def derive_unit(value: object, unit: str, precision: object, *, percent_sign: str) -> str:
    """Apply a ``unit`` to ``value``. Raises ``ValueError`` on a bad entry."""
    if unit not in SUPPORTED_UNITS:
        raise ValueError(f"unsupported unit {unit!r}; supported: {', '.join(SUPPORTED_UNITS)}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"unit={unit!r} requires a numeric fraction value, got {value!r}")
    if isinstance(precision, bool) or not isinstance(precision, int) or precision < 0:
        raise ValueError(f"precision must be a non-negative int, got {precision!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"unit={unit!r} requires a finite value, got {value!r}")
    d = Decimal(repr(value)) if isinstance(value, float) else Decimal(value)
    with localcontext() as ctx:
        # Enough digits that quantize never overflows for large magnitudes.
        ctx.prec = max(28, d.adjusted() + precision + 5)
        if unit == "percent":
            d = d * 100
        try:
            text = str(d.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP))
        except InvalidOperation as exc:
            raise ValueError(f"cannot render {value!r} at precision {precision}") from exc
    if text in ("-0", "-0." + "0" * precision):
        text = text[1:]
    return text + (percent_sign if unit == "percent" else "")


def natural(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def parse_precision(raw: str | None):
    """A span's ``data-precision`` attribute as an int, or an error string."""
    if raw is None:
        return None
    raw = raw.strip()
    # ASCII digits only: str.isdigit() also accepts "²", which int() rejects.
    if not re.fullmatch(r"[0-9]+", raw):
        return f"data-precision={raw!r} must be a non-negative integer"
    return int(raw)


def rendered_tex(entry) -> Expected | None:
    """What a generated TeX macro expands to when that differs from the stored
    value: the ``unit`` rendering (``96.5\\%``) or the ``display`` override.
    ``None`` for a natural rendering; ``Expected.problem`` set when the entry's
    ``unit`` / ``precision`` cannot be rendered."""
    if entry.unit is not None:
        try:
            return Expected(text=derive_unit(entry.value, entry.unit, entry.precision,
                                             percent_sign="\\%"), exact=True)
        except ValueError as exc:
            return Expected(text=None, exact=True, problem=str(exc))
    if entry.display is not None:
        return Expected(text=str(entry.display), exact=True)
    return None


# TeX spacing that may sit inside a number-with-unit (``96.5\\,\\%``).
TEX_SPACING = r"[ \t\n~]|\\[,;: ]|\\thinspace\b"
_TEX_SPACING_RE = re.compile(TEX_SPACING)
_PLAIN_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def tex_snapshot_matches_rendered(snapshot: str, rendered: str) -> bool:
    """True if ``snapshot`` spells the same rendered TeX as ``rendered``,
    ignoring TeX spacing (``96.5\\,\\%``, ``96.5~\\%``) and, for a number,
    trailing zeros (``96.50\\%``)."""
    want = _TEX_SPACING_RE.sub("", rendered)
    suffix = "\\%" if want.endswith("\\%") else ""
    want_n = want[: len(want) - len(suffix)]
    if not _PLAIN_NUMBER_RE.fullmatch(want_n):
        # A text ``display`` ("not significant", "95\\% CI"): its spaces are
        # meaningful; only runs of whitespace collapse.
        return " ".join(snapshot.split()) == " ".join(rendered.split())
    snap = _TEX_SPACING_RE.sub("", snapshot)
    if suffix and not snap.endswith(suffix):
        return False
    snap_n = snap[: len(snap) - len(suffix)]
    if not _PLAIN_NUMBER_RE.fullmatch(snap_n):
        return False
    return normalize_number(snap_n) == normalize_number(want_n)


def normalize_number(number: str) -> str:
    """``97.00`` → ``97``, ``96.50`` → ``96.5``: trailing fractional zeros dropped."""
    return number.rstrip("0").rstrip(".") if "." in number else number


def looks_rendered(snapshot: str, rendered: str) -> bool:
    """Whether a (stale) snapshot is written in the rendered style rather than
    as the stored value — so ``--write`` can keep the author's choice. A
    percent rendering ⇒ the snapshot has ``\\%``; a plain-number rendering ⇒
    the snapshot has the same number of decimals; any other ``display`` ⇒
    the snapshot is not a plain number."""
    snap = _TEX_SPACING_RE.sub("", snapshot)
    want = _TEX_SPACING_RE.sub("", rendered)
    if want.endswith("\\%"):
        return snap.endswith("\\%")
    if _PLAIN_NUMBER_RE.fullmatch(want):
        if not _PLAIN_NUMBER_RE.fullmatch(snap):
            return False
        decimals = lambda n: len(n.partition(".")[2])  # noqa: E731
        return decimals(snap) == decimals(want)
    return not _PLAIN_NUMBER_RE.fullmatch(snap)


def expected_html(entry, precision_override: int | None = None) -> Expected:
    """Expected rendered text of an HTML wrapper for manifest ``entry``."""
    if precision_override is not None and entry.unit is None:
        return Expected(
            text=None, exact=True,
            problem="data-precision applies only to entries with a unit (percent or decimal)",
        )
    if entry.unit is not None:
        precision = entry.precision if precision_override is None else precision_override
        try:
            text = derive_unit(entry.value, entry.unit, precision, percent_sign="%")
        except ValueError as exc:
            return Expected(text=None, exact=True, problem=str(exc))
        return Expected(text=text, exact=True)
    if entry.display_html is not None:
        markup = str(entry.display_html)
        return Expected(text=rendered_text(markup), exact=True, markup=markup)
    if entry.display is not None and not _TEX_MARKUP_RE.search(str(entry.display)):
        return Expected(text=str(entry.display), exact=True)
    if entry.display is not None:
        return Expected(
            text=None,
            exact=True,
            problem=(
                "manifest entry has a TeX-only 'display' override; add a "
                "'display_html' string so the HTML rendering can be checked"
            ),
        )
    return Expected(text=natural(entry.value), exact=isinstance(entry.value, str))


def derived_forms(manifest, fmt: str):
    """``(entry, number_text, suffix)`` for every entry whose display is
    derived from a ``unit`` — the rendered forms a raw literal can take.
    ``suffix`` is the percent sign as written in ``fmt`` (``\\%`` in TeX).

    Only fractional percents count (``95.4%``): the percent sign plus a
    decimal part is specific enough to attribute a literal to one value. A
    rounded ``decimal`` rendering (``1.5``) or an integer percent (``95%``)
    is not evidence — many unrelated literals round to it — so those fall to
    ``unsourced-numeric-token`` instead."""
    out = []
    sign = "%" if fmt == "html" else "\\%"
    for entry in manifest.numbers:
        if entry.unit != "percent" or entry.value is None:
            continue
        try:
            text = derive_unit(entry.value, entry.unit, entry.precision, percent_sign="")
        except ValueError:
            continue
        if "." not in text:
            continue
        out.append((entry, text, sign if entry.unit == "percent" else ""))
    return out
