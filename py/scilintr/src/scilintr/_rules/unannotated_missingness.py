"""unannotated-missingness — fillna / nan_to_num / errors='coerce' without justification."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unannotated-missingness"
MESSAGE = (
    "imputation / coercion without justification — explain what's being filled and where it's "
    "recorded, or add ANALYSIS_OK[missingness] / ANALYSIS_OK[imputation]"
)


def _is_fillna(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr == "fillna"


def _is_nan_to_num(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr == "nan_to_num"


def _is_coerce_numeric(node: ast.Call) -> bool:
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "to_numeric":
        return False
    for kw in node.keywords:
        if kw.arg == "errors" and isinstance(kw.value, ast.Constant) and kw.value.value == "coerce":
            return True
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_fillna(node) or _is_nan_to_num(node) or _is_coerce_numeric(node):
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
