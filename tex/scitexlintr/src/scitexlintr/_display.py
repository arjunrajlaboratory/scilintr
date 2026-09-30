"""Display formatting — how a manifest value is rendered in a report.

This is the single definition of the ``unit`` / ``precision`` / ``display``
contract. mycelium's ``render_report_values_tex`` applies the same rules
when it emits TeX macros; the HTML frontend uses them to check (and, with
``--write``, rewrite) the rendered text of every ``data-sci-val`` span.
Only the escaping differs between the two formats: TeX renders a percent
as ``97.8\\%``, HTML as ``97.8%``.

Selection order, identical in both formats:

1. ``unit`` set — derive the string from ``value``. ``unit="percent"`` turns
   the stored fraction ``0.978`` into ``97.8%`` at ``precision`` decimal
   places (default 1).
2. a format-specific override — ``display`` (TeX, verbatim) or
   ``display_html`` (HTML, verbatim).
3. neither — the natural form of the value.
"""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_UNITS = ("percent",)


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


def derive_unit(value: object, unit: str, precision: object, *, percent_sign: str) -> str:
    """Apply a ``unit`` to ``value``. Raises ``ValueError`` on a bad entry."""
    if unit not in SUPPORTED_UNITS:
        raise ValueError(f"unsupported unit {unit!r}; supported: {', '.join(SUPPORTED_UNITS)}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"unit={unit!r} requires a numeric fraction value, got {value!r}")
    if isinstance(precision, bool) or not isinstance(precision, int) or precision < 0:
        raise ValueError(f"precision must be a non-negative int, got {precision!r}")
    return f"{value * 100:.{precision}f}" + percent_sign


def natural(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def expected_html(entry) -> Expected:
    """Expected rendered text of an HTML wrapper for manifest ``entry``."""
    if entry.unit is not None:
        try:
            text = derive_unit(entry.value, entry.unit, entry.precision, percent_sign="%")
        except ValueError as exc:
            return Expected(text=None, exact=True, problem=str(exc))
        return Expected(text=text, exact=True)
    if entry.display_html is not None:
        return Expected(text=str(entry.display_html), exact=True)
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
