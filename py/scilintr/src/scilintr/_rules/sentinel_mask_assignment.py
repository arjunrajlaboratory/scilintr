"""sentinel-mask-assignment — assigning a boolean mask from a sentinel comparison.

The bad shape is ``<name> = <expr> != ""`` (or ``== ""``) at statement level, where
the mask is implicitly the partitioner that downstream filters use. Distinct from
``unannotated-filter``, which catches the same idea inline inside a subscript
(``df[df["x"] != ""]``).

Scope, on purpose:

* Only the empty-string sentinel is matched. Numeric ``!= 0`` and ``is not None`` are
  out of scope — too common and usually legitimate.
* Only literal targets (``Assign`` / ``AnnAssign`` to a ``Name``). Walrus and tuple
  unpacking are not handled.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "sentinel-mask-assignment"
MESSAGE = (
    "assigning a boolean mask from `<expr> != \"\"` / `== \"\"` — the empty string is "
    "being used as a missingness sentinel, which downstream code will then quietly "
    "filter against. Use real nullability (`.notna()`, `pd.isna`) or "
    "add ANALYSIS_OK[sentinel-mask] documenting the upstream contract"
)


def _is_empty_string_compare(value: ast.AST) -> bool:
    if not isinstance(value, ast.Compare):
        return False
    if not any(isinstance(op, (ast.NotEq, ast.Eq)) for op in value.ops):
        return False
    return any(
        isinstance(c, ast.Constant) and c.value == "" for c in value.comparators
    )


def _value_contains_sentinel_compare(value: ast.AST) -> bool:
    """True if ``value`` is — or recursively wraps — an empty-string Compare via
    pandas vectorized boolean ops (``&``, ``|``, ``~``).

    Pandas masks compose with ``BitAnd`` / ``BitOr`` / ``Invert`` (BinOp / UnaryOp).
    Scalar Python ``and``/``or`` (``BoolOp``) is intentionally not traversed —
    that builds a scalar boolean, not a mask, and is out of scope.
    """
    if _is_empty_string_compare(value):
        return True
    if isinstance(value, ast.BinOp) and isinstance(value.op, (ast.BitAnd, ast.BitOr)):
        return _value_contains_sentinel_compare(value.left) or _value_contains_sentinel_compare(value.right)
    if isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.Invert):
        return _value_contains_sentinel_compare(value.operand)
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _value_contains_sentinel_compare(node.value):
            if any(isinstance(t, ast.Name) for t in node.targets):
                findings.append(
                    Finding(
                        rule=CODE,
                        line=node.lineno,
                        col=node.col_offset,
                        message=MESSAGE,
                        severity="hard-fail",
                    )
                )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None and _value_contains_sentinel_compare(node.value):
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
