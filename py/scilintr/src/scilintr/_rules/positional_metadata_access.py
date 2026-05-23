"""positional-metadata-access — anonymous ``.iloc[..., INT]`` subscripts."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "positional-metadata-access"
MESSAGE = (
    "anonymous positional `.iloc` access with a numeric literal — name the column "
    "(use df['col_name']) or add a named constant + assertion and ANALYSIS_OK[positional-access]"
)


def _is_int_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool)


def _slice_has_column_int_literal(slc: ast.AST) -> bool:
    """Return True if the slice positionally indexes a *column* with an int literal.

    A bare ``iloc[0]`` selects a row by position — common and not the target of this
    rule. ``iloc[:, 3]`` (or ``iloc[5, 3]``) selects a column by position, which is
    exactly the anonymous-column-access pattern the rule cares about.
    """
    if not isinstance(slc, ast.Tuple) or len(slc.elts) < 2:
        return False
    # Any int literal in non-first (column-axis) position counts.
    return any(_is_int_literal(e) for e in slc.elts[1:])


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        if not isinstance(node.value, ast.Attribute) or node.value.attr != "iloc":
            continue
        if not _slice_has_column_int_literal(node.slice):
            continue
        findings.append(
            Finding(
                rule=CODE,
                line=node.lineno,
                col=node.col_offset,
                message=MESSAGE,
                severity="structured-comment",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check)
