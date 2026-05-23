"""unannotated-filter — silent .dropna() or empty-string sentinel filter.

Detects two shapes:

1. ``df.dropna()`` calls.
2. ``df[df[col] != ""]`` or ``df[df[col] != None]`` — the "sentinel then filter"
   pattern where missing/unmappable rows were given a sentinel and are now silently
   excluded.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unannotated-filter"
MESSAGE = (
    "silent row filter without justification — record what's dropped (helper + ledger) "
    "or add ANALYSIS_OK[sample-filter] / ANALYSIS_OK[feature-filter]"
)


def _is_dropna_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "dropna"
    )


def _is_empty_string_sentinel(node: ast.AST) -> bool:
    # Only flag the empty-string sentinel. `is None`/`is not None` is the standard
    # idiom for null filtering and is not in scope of this rule.
    return isinstance(node, ast.Constant) and node.value == ""


def _slice_is_sentinel_filter(slc: ast.AST) -> bool:
    if not isinstance(slc, ast.Compare):
        return False
    if not any(isinstance(op, (ast.NotEq, ast.Eq)) for op in slc.ops):
        return False
    return any(_is_empty_string_sentinel(c) for c in slc.comparators)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if _is_dropna_call(node):
            findings.append(
                Finding(
                    rule=CODE,
                    line=node.lineno,
                    col=node.col_offset,
                    message=MESSAGE,
                    severity="hard-fail",
                )
            )
        elif isinstance(node, ast.Subscript) and _slice_is_sentinel_filter(node.slice):
            findings.append(
                Finding(
                    rule=CODE,
                    line=node.lineno,
                    col=node.col_offset,
                    message=MESSAGE,
                    severity="hard-fail",
                )
            )
    return findings


rule = Rule(code=CODE, check=_check)
