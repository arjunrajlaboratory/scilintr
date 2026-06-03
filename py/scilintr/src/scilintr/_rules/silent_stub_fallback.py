"""silent-stub-fallback — ``except`` handler that defines a no-op / ``None``-returning stub.

A third silent-fallback costume, sibling to ``silent-pass`` and
``return-none-on-missing-input``: instead of dropping the failure with ``pass``
or guarding a missing file, the handler defines a stub function (or rebinds a
name to a no-op lambda) so the failure path silently degrades behavior instead
of raising. Same hidden commitment — "this side effect may silently not happen"
— expressed as a function def rather than ``pass``.

Caught in the wild only by an external reviewer; scilintr returned zero findings
on the exact commit because the except type was narrow (``ModuleNotFoundError``,
so ``broad-exception`` correctly skips it), the body was a ``FunctionDef`` not a
``Pass`` (so ``silent-pass`` missed it), and there was no ``.exists()`` guard (so
``return-none-on-missing-input`` missed it).
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "silent-stub-fallback"
MESSAGE = (
    "except handler defines a no-op/None-returning stub — the failure path silently degrades "
    "instead of raising; provide a real fallback, log + re-raise, or add "
    "ANALYSIS_OK[optional-dependency] with justification"
)


def _is_noop_stmt(stmt: ast.stmt) -> bool:
    # The building blocks of an empty body: `pass`, `return`/`return None`,
    # and a bare expression statement that is just a constant (`...` or a docstring).
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Return):
        return stmt.value is None or (
            isinstance(stmt.value, ast.Constant) and stmt.value.value is None
        )
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        return True
    return False


def _is_noop_function(node: ast.stmt) -> bool:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    body = node.body
    # Strip a single leading docstring so `def f(): "doc"; return None` still counts.
    if len(body) > 1 and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    return bool(body) and all(_is_noop_stmt(stmt) for stmt in body)


def _is_noop_lambda_rebind(node: ast.stmt) -> bool:
    # `name = lambda *a, **k: None` / `: ...` — the lambda spelling of a no-op stub.
    value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
    if not isinstance(value, ast.Lambda):
        return False
    body = value.body
    # `lambda: None` and `lambda: ...` are both no-op bodies (mirrors the def form).
    return isinstance(body, ast.Constant) and (body.value is None or body.value is Ellipsis)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        for stmt in node.body:
            if _is_noop_function(stmt) or _is_noop_lambda_rebind(stmt):
                # Anchor at the stub itself, not the `except` keyword, so a waiver
                # comment placed inside the except body suppresses the finding
                # (same rationale as silent-pass).
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
