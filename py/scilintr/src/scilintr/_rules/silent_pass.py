"""silent-pass — except handler whose body is just ``pass`` or ``continue``."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "silent-pass"
MESSAGE = (
    "except body is a silent `pass`/`continue` — failures are dropped without log, raise, or recovery; "
    "log the exception, narrow the type, or add ANALYSIS_OK[best-effort-fan-out] with justification"
)


def _is_silent(body: list[ast.stmt]) -> bool:
    if len(body) != 1:
        return False
    stmt = body[0]
    return isinstance(stmt, (ast.Pass, ast.Continue))


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and _is_silent(node.body):
            silent_stmt = node.body[0]
            # Anchor at the silent pass/continue itself, not the except keyword.
            # This lets a waiver comment placed inside the except body suppress
            # the finding correctly (the comment is line-above; finding is below).
            findings.append(
                Finding(
                    rule=CODE,
                    line=silent_stmt.lineno,
                    col=silent_stmt.col_offset,
                    message=MESSAGE,
                    severity="hard-fail",
                )
            )
    return findings


rule = Rule(code=CODE, check=_check)
