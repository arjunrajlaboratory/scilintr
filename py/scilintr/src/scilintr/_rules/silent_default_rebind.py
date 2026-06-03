"""silent-default-rebind — ``except`` body that rebinds a name to a default value.

Fifth silent-fallback costume: the handler assigns a placeholder (``{}`` / ``[]``
/ ``None`` / ``0`` / ``NaN``) to a name on the failure path, so the analysis
continues on a degraded value instead of raising. The value-rebind counterpart
to ``silent-stub-fallback`` (which rebinds to a no-op *callable*) and the
assignment counterpart to ``silent-fallback-return``.

Rebinding to a *real* recovered value (an alternate loader, a computed default)
is legitimate and left alone — only placeholder values are flagged.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule
from scilintr._rules._degraded_default import is_degraded_default

CODE = "silent-default-rebind"
MESSAGE = (
    "except body rebinds a name to a degraded default (None/empty/0/NaN) — the analysis "
    "silently continues on a placeholder instead of raising; raise, recover a real value, or add "
    "ANALYSIS_OK[optional-input] with justification"
)


def _rebound_default(stmt: ast.stmt) -> ast.stmt | None:
    """Return the assignment node if it rebinds a name to a degraded default."""
    if isinstance(stmt, ast.Assign) and is_degraded_default(stmt.value):
        return stmt
    # AnnAssign with no value (`x: int`) is annotation-only, not a rebind — skip it.
    if isinstance(stmt, ast.AnnAssign) and stmt.value is not None and is_degraded_default(stmt.value):
        return stmt
    return None


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        # Direct statements only — an assignment nested in a stub def is that def's concern.
        for stmt in node.body:
            hit = _rebound_default(stmt)
            if hit is not None:
                findings.append(
                    Finding(
                        rule=CODE,
                        line=hit.lineno,
                        col=hit.col_offset,
                        message=MESSAGE,
                        severity="hard-fail",
                    )
                )
    return findings


rule = Rule(code=CODE, check=_check)
