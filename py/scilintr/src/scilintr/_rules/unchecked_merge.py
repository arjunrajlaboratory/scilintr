"""unchecked-merge — pandas ``.merge(...)`` without ``validate=`` cardinality check."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unchecked-merge"
MESSAGE = (
    "`.merge()` without `validate=` — inner joins silently drop rows when keys don't match; "
    "pass validate='one_to_one'/'one_to_many' or add ANALYSIS_OK[join]"
)


def _is_merge_call(node: ast.Call) -> bool:
    # `df.merge(...)` and `pd.merge(...)` both parse as Attribute access.
    if isinstance(node.func, ast.Attribute) and node.func.attr == "merge":
        return True
    # `from pandas import merge; merge(a, b)` parses as a bare Name call.
    if isinstance(node.func, ast.Name) and node.func.id == "merge":
        return True
    return False


def _has_validate(node: ast.Call) -> bool:
    return any(kw.arg == "validate" for kw in node.keywords)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_merge_call(node):
            continue
        if _has_validate(node):
            continue
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
