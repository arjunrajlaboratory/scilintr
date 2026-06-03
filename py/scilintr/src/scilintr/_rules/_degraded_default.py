"""Shared predicate for the silent-fallback-*value* family.

``silent-fallback-return`` (a degraded ``return``) and ``silent-default-rebind``
(a degraded assignment) flag the same set of placeholder values — ``None``,
empty container, ``0``, empty string, ``NaN``. Keeping that set in one place
means a future addition (say ``pd.NA``) lands in both rules at once, rather than
drifting between two copies — the very kind of divergence scilintr exists to catch.
"""

from __future__ import annotations

import ast
import math


def is_degraded_default(expr: ast.expr | None) -> bool:
    """True if ``expr`` is a placeholder/degraded value (None/empty/0/""/NaN).

    ``None`` (the AST node, e.g. a bare ``return``) counts as degraded.
    """
    if expr is None:  # bare `return`
        return True
    if isinstance(expr, ast.Constant):
        value = expr.value
        if isinstance(value, bool):  # `False`/`True` is a real result, not a placeholder
            return False
        if value is None or value == "":
            return True
        if isinstance(value, (int, float)) and value == 0:
            return True
        if isinstance(value, float) and math.isnan(value):
            return True
        return False
    if isinstance(expr, ast.List) and not expr.elts:
        return True
    if isinstance(expr, ast.Tuple) and not expr.elts:
        return True
    if isinstance(expr, ast.Dict) and not expr.keys:
        return True
    # np.nan / numpy.nan / math.nan
    if isinstance(expr, ast.Attribute) and expr.attr == "nan":
        return True
    # float("nan")
    if (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id == "float"
        and expr.args
        and isinstance(expr.args[0], ast.Constant)
        and isinstance(expr.args[0].value, str)
        and expr.args[0].value.strip().lower() == "nan"
    ):
        return True
    return False
