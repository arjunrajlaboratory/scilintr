"""magic-threshold — bare numeric literal as the comparator in a DataFrame boolean filter.

Triggered by ``Compare`` nodes whose comparator is a numeric ``Constant`` and whose
parent is a ``Subscript`` slice. This catches the canonical volcano-style
``df[df['padj'] < 0.05]`` pattern without flagging garden-variety ``if x < 5:``.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "magic-threshold"
MESSAGE = (
    "numeric literal used as a threshold in a DataFrame boolean filter — "
    "promote to a named constant (e.g., FDR_THRESHOLD) or add ANALYSIS_OK[threshold]"
)


def _is_numeric_literal(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    )


def _is_natural_floor(op: ast.cmpop, value) -> bool:
    """``> 0`` / ``>= 0`` is a natural floor, not a tunable cutoff.

    Dropping empty/zero entries (``deg[deg > 0]``, ``p[p >= 0]``) selects the
    participating elements / keeps a log defined; ``0`` is the algebraic floor of
    a count or probability, almost never a *chosen* threshold. Only literal ``0``
    under ``>`` / ``>=`` qualifies — ``> 1`` is a real cutoff, and ``< 0`` is a
    sign filter, so both stay flagged.
    """
    return isinstance(op, (ast.Gt, ast.GtE)) and value == 0


def _flag_compare(node: ast.Compare) -> bool:
    return any(
        _is_numeric_literal(comparator) and not _is_natural_floor(op, comparator.value)
        for op, comparator in zip(node.ops, node.comparators)
    )


def _walk_subscript_filters(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            yield node.slice


def _walk_compares(node: ast.AST):
    """Yield Compare nodes inside slice expressions, recursing through BoolOp/BinOp/UnaryOp.

    pandas vectorized filters use ``|`` / ``&`` (BitOr/BitAnd) and ``~`` (Invert),
    not boolean ``and``/``or``. Both forms must be traversed.
    """
    if isinstance(node, ast.Compare):
        yield node
        return
    if isinstance(node, ast.BoolOp):
        for v in node.values:
            yield from _walk_compares(v)
        return
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitOr, ast.BitAnd)):
        yield from _walk_compares(node.left)
        yield from _walk_compares(node.right)
        return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
        yield from _walk_compares(node.operand)
        return


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for slc in _walk_subscript_filters(tree):
        for cmp in _walk_compares(slc):
            if _flag_compare(cmp):
                findings.append(
                    Finding(
                        rule=CODE,
                        line=cmp.lineno,
                        col=cmp.col_offset,
                        message=MESSAGE,
                        severity="structured-comment",
                    )
                )
    return findings


rule = Rule(code=CODE, check=_check)
