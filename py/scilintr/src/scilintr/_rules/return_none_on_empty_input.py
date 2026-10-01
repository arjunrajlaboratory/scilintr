"""return-none-on-empty-input (opt-in) — ``if df is None: return None``.

The "upstream already missing / empty" sibling of
``return-none-on-missing-input``: a guard on ``x is None``, ``len(x) == 0``,
``not len(x)``, ``not x`` or pandas' ``x.empty`` that returns a degraded
placeholder passes the absence on instead of failing where it started.

Optional parameters legitimately short-circuit on ``None`` all the time, so
this rule is opt-in: it runs only when named in ``rules=`` / ``--rules``.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule
from scilintr._rules.return_none_on_missing_input import degraded_return

CODE = "return-none-on-empty-input"
MESSAGE = (
    "returning a placeholder when the input is None/empty silently propagates absence "
    "downstream; raise where the input should exist, or add ANALYSIS_OK[optional-input] "
    "with justification"
)


def _is_len_call(expr: ast.expr) -> bool:
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "len"
        and len(expr.args) == 1
    )


def _is_const(expr: ast.expr, value: int) -> bool:
    return isinstance(expr, ast.Constant) and type(expr.value) is int and expr.value == value


def _is_empty_test(test: ast.expr) -> bool:
    # `x.empty` (pandas)
    if isinstance(test, ast.Attribute) and test.attr == "empty":
        return True
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        inner = test.operand
        # `not x.empty` means "has data" — the opposite guard
        if isinstance(inner, ast.Attribute) and inner.attr == "empty":
            return False
        # `not x` / `not self.x` — a plain value, not a predicate call
        if isinstance(inner, (ast.Name, ast.Attribute)):
            return True
        # `not len(x)`
        return _is_len_call(inner)
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        left, op, right = test.left, test.ops[0], test.comparators[0]
        # `x is None`
        if isinstance(op, ast.Is) and isinstance(right, ast.Constant) and right.value is None:
            return True
        # `len(x) == 0`, `0 == len(x)`, `len(x) < 1`
        if isinstance(op, ast.Eq):
            return (_is_len_call(left) and _is_const(right, 0)) or (
                _is_const(left, 0) and _is_len_call(right)
            )
        if isinstance(op, ast.Lt):
            return _is_len_call(left) and _is_const(right, 1)
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not _is_empty_test(node.test):
            continue
        ret = degraded_return(node.body)
        if ret is None:
            continue
        findings.append(
            Finding(
                rule=CODE,
                line=ret.lineno,
                col=ret.col_offset,
                message=MESSAGE,
                severity="structured-comment",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check, opt_in=True)
