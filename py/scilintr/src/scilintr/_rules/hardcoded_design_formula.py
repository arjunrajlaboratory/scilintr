"""hardcoded-design-formula — string formulas / contrast tuples assigned to design vars."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "hardcoded-design-formula"
MESSAGE = (
    "design formula / contrast hard-coded in source — read from a config so the report and "
    "code agree, or add ANALYSIS_OK[contrast-definition]"
)

_DESIGN_VARS = {"formula", "design", "contrast"}


def _is_formula_constant(value: ast.AST) -> bool:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        # very loose: anything containing "~" is a formula
        return "~" in value.value
    return False


def _is_contrast_tuple(value: ast.AST) -> bool:
    if not isinstance(value, ast.Tuple):
        return False
    if len(value.elts) < 2:
        return False
    return all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in value.elts)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        triggers = _is_formula_constant(node.value) or _is_contrast_tuple(node.value)
        if not triggers:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in _DESIGN_VARS:
                findings.append(
                    Finding(
                        rule=CODE,
                        line=node.lineno,
                        col=node.col_offset,
                        message=MESSAGE,
                        severity="structured-comment",
                    )
                )
                break
    return findings


rule = Rule(code=CODE, check=_check)
