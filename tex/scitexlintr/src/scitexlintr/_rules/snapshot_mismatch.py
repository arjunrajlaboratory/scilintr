"""snapshot-mismatch — \\SciVal{\\Macro}{snapshot} where snapshot ≠ manifest value.

The cardinal scitexlintr check: the human-readable snapshot in the second
argument of every wrapper macro must agree with the value that the macro
expands to. Drift = lint error. Auto-fixable via ``--write``.
"""

from __future__ import annotations

from scitexlintr._doc import TexDoc, extract_macro_ref
from scitexlintr._finding import Finding, Fix
from scitexlintr._manifest import Manifest, values_equal_as_snapshot
from scitexlintr._rules._base import Rule

CODE = "snapshot-mismatch"


def _check(doc: TexDoc, manifest: Manifest | None) -> list[Finding]:
    if manifest is None:
        return []
    findings: list[Finding] = []
    for wrapper_name in ("SciVal", "SciText"):
        for call in doc.calls(wrapper_name):
            if len(call.args) < 2:
                continue
            macro_name = extract_macro_ref(call.args[0].text)
            if macro_name is None:
                continue
            entry = manifest.by_macro.get(macro_name)
            if entry is None:
                continue
            snap_arg = call.args[1]
            snap_text = snap_arg.text
            if values_equal_as_snapshot(entry.value, snap_text):
                continue
            line, col = doc.lookup(snap_arg.start)
            findings.append(
                Finding(
                    rule=CODE,
                    line=line,
                    col=col,
                    message=(
                        f"snapshot {_quote(snap_text.strip())} for \\{macro_name} "
                        f"disagrees with manifest value {_quote(entry.value)} "
                        f"(id={entry.id})"
                    ),
                    severity="error",
                    fix=Fix(
                        start=snap_arg.start + 1,           # inside the brace
                        end=snap_arg.end - 1,
                        replacement=str(_format_for_fix(entry.value)),
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
    return str(value)


rule = Rule(code=CODE, check=_check, requires_manifest=True)
