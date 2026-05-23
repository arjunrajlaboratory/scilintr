"""broad-exception — ``except Exception`` or bare ``except`` clauses."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "broad-exception"
MESSAGE = (
    "broad `except Exception` swallows unrelated errors; "
    "catch a specific exception type or add ANALYSIS_OK[api-retry] with justification"
)


def _is_broad(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    if isinstance(handler.type, ast.Name) and handler.type.id in {"Exception", "BaseException"}:
        return True
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and _is_broad(node):
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
