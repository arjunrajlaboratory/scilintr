"""runtime-assert — ``assert`` outside ``tests/`` used as a runtime correctness check.

``assert`` statements are stripped under ``python -O``. Anything load-bearing
must raise explicitly. ``assert False, "TODO"`` and similar literal-tripwire
asserts are ignored — those are obvious developer intent, not runtime checks.
"""

from __future__ import annotations

import ast
import os

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "runtime-assert"
MESSAGE = (
    "`assert` is stripped under `python -O` — for runtime checks raise explicitly; "
    "or add ANALYSIS_OK[runtime-assert] documenting that this is a developer tripwire"
)


def _is_test_file(filename: str) -> bool:
    parts = filename.replace("\\", "/").split("/")
    # Recognize tests/, test/, and any *_tests/ subdirectory (integration_tests,
    # e2e_tests, unit_tests, ...).
    for p in parts:
        low = p.lower()
        if low in {"tests", "test"} or low.endswith("_tests"):
            return True
    base = os.path.basename(filename).lower()
    return base.startswith("test_") or base.endswith("_test.py")


def _is_literal_tripwire(test: ast.AST) -> bool:
    """`assert False`, `assert True`, `assert 0` — literal constants are dev-intent."""
    return isinstance(test, ast.Constant)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    if _is_test_file(filename):
        return []

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        if _is_literal_tripwire(node.test):
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
