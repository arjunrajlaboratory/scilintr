"""warning-suppression — ``warnings.filterwarnings('ignore')`` without a category or module narrowing."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "warning-suppression"
MESSAGE = (
    "global warning suppression — narrow the filter with category=/module= or "
    "add ANALYSIS_OK[warning-suppression] explaining which warnings are being silenced and why"
)


def _is_filterwarnings_ignore_all(node: ast.Call) -> bool:
    func = node.func
    if not isinstance(func, ast.Attribute) or func.attr != "filterwarnings":
        return False
    # first positional arg must be "ignore"
    if not node.args:
        return False
    first = node.args[0]
    if not (isinstance(first, ast.Constant) and first.value == "ignore"):
        return False
    # narrowing kwargs disqualify
    narrowed = any(kw.arg in {"category", "module", "message"} for kw in node.keywords)
    return not narrowed


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_filterwarnings_ignore_all(node):
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
