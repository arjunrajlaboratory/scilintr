"""snapshot-mismatch — \\SciVal{\\Macro}{snapshot} where snapshot ≠ manifest value.

The cardinal scitexlintr check: the human-readable snapshot in the second
argument of every wrapper macro must agree with the value that the macro
expands to — either the stored manifest value (``0.9653``) or, for an entry
with a ``unit`` or ``display``, its rendered form (``96.5\\%``). Drift =
lint error. Auto-fixable via ``--write``.

HTML has no macro expansion, so the rendered text of a
``<span data-sci-val="id">…</span>`` wrapper *is* the snapshot. It must
equal the manifest value rendered through the ``unit`` / ``precision`` /
``display_html`` contract in ``_display``; ``--write`` rewrites it.
"""

from __future__ import annotations

import html

from scitexlintr._display import (
    expected_html,
    parse_precision,
    looks_rendered,
    rendered_tex,
    tex_snapshot_matches_rendered,
)
from scitexlintr._doc import TexDoc, extract_macro_ref
from scitexlintr._finding import Finding, Fix
from scitexlintr._manifest import Manifest, values_equal_as_snapshot
from scitexlintr._parser import WRAPPER_MACROS
from scitexlintr._rules._base import Rule

CODE = "snapshot-mismatch"


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    if doc.fmt == "html":
        return _check_html(doc, manifest)
    findings: list[Finding] = []
    unrenderable: set[str] = set()
    for wrapper_name in sorted(WRAPPER_MACROS):
        for call in doc.calls(wrapper_name):
            if len(call.args) < 2:
                continue
            macro_name = extract_macro_ref(call.args[0].text)
            if macro_name is None:
                continue
            entry = manifest.by_macro.get(macro_name)
            if entry is None:
                continue  # unknown macros belong to unknown-value-id
            if entry.value is None:
                # Null manifest values can't be compared. Skip the rule —
                # emitting a Fix would otherwise rewrite the snapshot to
                # the literal string 'None'.
                continue
            snap_arg = call.args[1]
            snap_text = snap_arg.text
            line, col = doc.lookup(snap_arg.start)
            if values_equal_as_snapshot(entry.value, snap_text):
                continue
            rendered = rendered_tex(entry)
            if rendered is not None and rendered.problem is not None:
                # One manifest defect, one finding — not one per wrapper.
                if entry.id not in unrenderable:
                    unrenderable.add(entry.id)
                    findings.append(Finding(
                        rule=CODE, line=line, col=col, severity="error",
                        message=f"cannot check snapshot for id={entry.id}: {rendered.problem}",
                    ))
                continue
            # A unit / display entry may also be snapshotted as it renders
            # (``96.5\%`` for a stored 0.9653) — what the PDF shows.
            if rendered is not None and tex_snapshot_matches_rendered(snap_text, rendered.text):
                continue
            # --write keeps the author's style: a stale snapshot written in the
            # rendered style is rewritten to the rendered form.
            keep_rendered = rendered is not None and looks_rendered(snap_text, rendered.text)
            replacement = rendered.text if keep_rendered else str(_format_for_fix(entry.value))
            renders_as = (
                f", which renders as {_quote(rendered.text)}" if rendered is not None else ""
            )
            findings.append(
                Finding(
                    rule=CODE,
                    line=line,
                    col=col,
                    message=(
                        f"snapshot {_quote(snap_text.strip())} for \\{macro_name} "
                        f"disagrees with manifest value {_quote(entry.value)}{renders_as} "
                        f"(id={entry.id})"
                    ),
                    severity="error",
                    fix=Fix(
                        start=snap_arg.start + 1,           # inside the brace
                        end=snap_arg.end - 1,
                        replacement=replacement,
                    ),
                )
            )
    return findings


def _check_html(doc, manifest: Manifest) -> list[Finding]:
    findings: list[Finding] = []
    for w in doc.wrappers:
        entry = manifest.resolve_number(w.key)
        if entry is None:
            continue  # unknown ids belong to unknown-value-id
        line, col = doc.lookup(w.inner_start)
        if entry.value is None:
            # Wrapper text is excluded from prose, so a span backed by no value
            # would otherwise vouch for any number typed into it.
            findings.append(Finding(rule=CODE, line=line, col=col, severity="error",
                                    message=f"id={entry.id} has no value in the manifest; "
                                            "the rendered text cannot be checked"))
            continue
        precision = parse_precision(w.precision)
        if isinstance(precision, str):
            findings.append(Finding(rule=CODE, line=line, col=col, severity="error",
                                    message=f"id={entry.id}: {precision}"))
            continue
        expected = expected_html(entry, precision)
        if expected.problem is not None:
            findings.append(
                Finding(
                    rule=CODE, line=line, col=col, severity="error",
                    message=f"cannot check rendered value for id={entry.id}: {expected.problem}",
                )
            )
            continue
        if expected.exact:
            ok = w.text == " ".join(expected.text.split())
        else:
            ok = values_equal_as_snapshot(entry.value, w.text)
        if ok:
            continue
        findings.append(
            Finding(
                rule=CODE,
                line=line,
                col=col,
                message=(
                    f"rendered value {_quote(w.text)} disagrees with manifest "
                    f"id={entry.id}, which renders as {_quote(expected.text)}"
                ),
                severity="error",
                fix=Fix(
                    start=w.inner_start,
                    end=w.inner_end,
                    replacement=expected.markup if expected.markup is not None else html.escape(expected.text, quote=False),
                    replaces_markup=expected.markup is not None and "<" in expected.markup,
                ),
            )
        )
    return findings


def _quote(v: object) -> str:
    s = str(v)
    if any(c.isspace() for c in s):
        return f'"{s}"'
    return s


def _format_for_fix(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return _tex_escape(value)
    return str(value)


# Characters that need a leading backslash to render as their literal selves
# in LaTeX prose. Ordered: ``\\`` first so it doesn't double-escape its own
# replacements. ``{`` and ``}`` are intentionally NOT escaped — they have
# meaning even inside argument groups and a snapshot containing braces is
# almost certainly broken upstream.
_TEX_ESCAPE_MAP = [
    ("\\", "\\textbackslash{}"),  # not strictly correct but never appears in numeric snapshots
    ("%", "\\%"),
    ("&", "\\&"),
    ("_", "\\_"),
    ("#", "\\#"),
    ("$", "\\$"),
    ("~", "\\textasciitilde{}"),
    ("^", "\\textasciicircum{}"),
]


def _tex_escape(s: str) -> str:
    """Escape TeX-special characters in a string snapshot.

    The unescaped form of a value like ``"50% done"`` would turn the rest
    of the line into a comment when written into the source. This is a
    minimal escaper covering the characters that BREAK the parse, not a
    full LaTeX renderer.
    """
    out = s
    for ch, esc in _TEX_ESCAPE_MAP:
        out = out.replace(ch, esc)
    return out


rule = Rule(code=CODE, check=_check, requires_manifest=True)
