"""unannotated-transform — combat / regress_out / remove_batch_effect / residualize calls."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unannotated-transform"
MESSAGE = (
    "scientifically consequential transform (combat / regress_out / residualize / remove_batch_effect) "
    "without justification — explain which covariates and why, or add ANALYSIS_OK[batch-correction] / "
    "ANALYSIS_OK[normalization]"
)

_TRANSFORM_NAMES = {
    "combat",
    "ComBat",
    "regress_out",
    "remove_batch_effect",
    "residualize",
}


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _called_name(node)
        if name in _TRANSFORM_NAMES:
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
