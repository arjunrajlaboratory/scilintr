"""ambiguous-layer-access — ``adata.X`` / ``adata.raw.X`` without an explicit layer name."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "ambiguous-layer-access"
MESSAGE = (
    "`.X` (or `.raw.X`) hides which expression layer is in use — read from `adata.layers[<name>]` "
    "or add ANALYSIS_OK[layer-choice] documenting which layer .X holds"
)


def _is_X_attr(node: ast.AST) -> bool:
    if not isinstance(node, ast.Attribute) or node.attr != "X":
        return False
    val = node.value
    if isinstance(val, ast.Name):
        return True
    # adata.raw.X
    if isinstance(val, ast.Attribute) and val.attr == "raw" and isinstance(val.value, ast.Name):
        return True
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if _is_X_attr(node):
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
