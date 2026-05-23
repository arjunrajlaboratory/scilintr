"""plot-side-effect-filter — DataFrame filtering happening inside plotting functions / files.

A boolean filter inside a ``plot_*`` function (or a file whose basename starts with
``plot``) is a side effect on the data, masquerading as visual styling.
"""

from __future__ import annotations

import ast
import os

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "plot-side-effect-filter"
MESSAGE = (
    "data is being filtered inside a plotting function — readers expect plot code to be a "
    "no-op on the data; move the filter upstream or add ANALYSIS_OK[plot-filter]"
)


def _is_plot_file(filename: str) -> bool:
    base = os.path.basename(filename).lower()
    return base.startswith("plot") or "plotting" in base


def _is_boolean_filter_subscript(node: ast.Subscript) -> bool:
    # df[df[col] OP value] — slice is Compare with at least one comparator that's not a literal.
    slc = node.slice
    if isinstance(slc, ast.Compare):
        return True
    if isinstance(slc, ast.BoolOp):
        return any(isinstance(v, ast.Compare) for v in slc.values)
    return False


def _walk_plot_function_bodies(tree: ast.AST):
    """Yield (function_def, body_node) pairs for functions whose name starts with `plot`."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("plot"):
            for inner in ast.walk(node):
                if inner is node:
                    continue
                yield node, inner


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    # In-file: any boolean filter inside a plot_-named function.
    seen_lines: set[int] = set()
    for func, inner in _walk_plot_function_bodies(tree):
        if isinstance(inner, ast.Subscript) and _is_boolean_filter_subscript(inner):
            if inner.lineno in seen_lines:
                continue
            seen_lines.add(inner.lineno)
            findings.append(
                Finding(
                    rule=CODE,
                    line=inner.lineno,
                    col=inner.col_offset,
                    message=MESSAGE,
                    severity="structured-comment",
                )
            )

    if _is_plot_file(filename):
        # Module-level filters in a plotting file also count.
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and _is_boolean_filter_subscript(node):
                if node.lineno in seen_lines:
                    continue
                seen_lines.add(node.lineno)
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
