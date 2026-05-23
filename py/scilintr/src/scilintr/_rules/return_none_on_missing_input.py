"""return-none-on-missing-input — ``if not <path>.exists(): return None``.

This is a fallback wearing a different costume — the caller propagates ``None``
through downstream merges and the analysis silently runs on a smaller frame.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "return-none-on-missing-input"
MESSAGE = (
    "returning None when input file is missing silently propagates absence downstream; "
    "raise FileNotFoundError or add ANALYSIS_OK[optional-input] with justification"
)


def _is_negated_exists_test(test: ast.expr) -> bool:
    # match `not <something>.exists()` or `not <something>.exists`
    if not isinstance(test, ast.UnaryOp) or not isinstance(test.op, ast.Not):
        return False
    inner = test.operand
    if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
        return inner.func.attr == "exists"
    return False


def _body_is_return_none(body: list[ast.stmt]) -> ast.Return | None:
    if not body:
        return None
    first = body[0]
    if isinstance(first, ast.Return):
        if first.value is None:
            return first
        if isinstance(first.value, ast.Constant) and first.value.value is None:
            return first
    return None


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not _is_negated_exists_test(node.test):
            continue
        ret = _body_is_return_none(node.body)
        if ret is None:
            continue
        findings.append(
            Finding(
                rule=CODE,
                line=ret.lineno,
                col=ret.col_offset,
                message=MESSAGE,
                severity="hard-fail",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check)
