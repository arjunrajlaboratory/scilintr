"""silent-fallback-return — ``except`` body that ``return``s a degraded default.

Fourth silent-fallback costume, sibling to ``silent-pass`` and
``silent-stub-fallback``: the handler returns a placeholder (``None`` / empty
container / ``0`` / ``NaN``) on the failure path instead of raising, so the
caller silently proceeds on a degraded value.

Only *degraded* returns are flagged. Returning a genuine recovery value (a
cache, an alternate computation) is legitimate and left alone — that is the
distinction from ``broad-exception``, which is about the *catch*, not the value.
"""

from __future__ import annotations

import ast
import math

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "silent-fallback-return"
MESSAGE = (
    "except body returns a degraded default (None/empty/0/NaN) — the failure path silently "
    "substitutes a placeholder instead of raising; raise, return a real recovery value, or add "
    "ANALYSIS_OK[degraded-fallback] with justification"
)


def _is_default_value(expr: ast.expr | None) -> bool:
    if expr is None:  # bare `return`
        return True
    if isinstance(expr, ast.Constant):
        value = expr.value
        if isinstance(value, bool):  # `return False`/`True` is a real result, not a placeholder
            return False
        if value is None or value == "":
            return True
        if isinstance(value, (int, float)) and value == 0:
            return True
        if isinstance(value, float) and math.isnan(value):
            return True
        return False
    if isinstance(expr, ast.List) and not expr.elts:
        return True
    if isinstance(expr, ast.Tuple) and not expr.elts:
        return True
    if isinstance(expr, ast.Dict) and not expr.keys:
        return True
    # np.nan / numpy.nan / math.nan
    if isinstance(expr, ast.Attribute) and expr.attr == "nan":
        return True
    # float("nan")
    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "float"
        and expr.args
        and isinstance(expr.args[0], ast.Constant)
        and isinstance(expr.args[0].value, str)
        and expr.args[0].value.strip().lower() == "nan"
    ):
        return True
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        # Only direct statements of the handler — a `return` nested in a stub def is
        # silent-stub-fallback's concern, not ours (avoids double-flagging).
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and _is_default_value(stmt.value):
                findings.append(
                    Finding(
                        rule=CODE,
                        line=stmt.lineno,
                        col=stmt.col_offset,
                        message=MESSAGE,
                        severity="hard-fail",
                    )
                )
    return findings


rule = Rule(code=CODE, check=_check)
