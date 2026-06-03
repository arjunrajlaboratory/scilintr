"""silent-fallback-return — ``except`` body that ``return``s a degraded default.

Fourth silent-fallback costume, sibling to ``silent-pass`` and
``silent-stub-fallback``: the handler returns a placeholder (``None`` / empty
container / ``0`` / ``NaN``) on the failure path instead of raising, so the
caller silently proceeds on a degraded value.

Only *degraded* returns are flagged. Returning a genuine recovery value (a
cache, an alternate computation) is legitimate and left alone — that is the
distinction from ``broad-exception``, which is about the *catch*, not the value.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule
from scilintr._rules._degraded_default import is_degraded_default

CODE = "silent-fallback-return"
MESSAGE = (
    "except body returns a degraded default (None/empty/0/NaN) — the failure path silently "
    "substitutes a placeholder instead of raising; raise, return a real recovery value, or add "
    "ANALYSIS_OK[degraded-fallback] with justification"
)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        # Only direct statements of the handler — a `return` nested in a stub def is
        # silent-stub-fallback's concern, not ours (avoids double-flagging).
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and is_degraded_default(stmt.value):
                findings.append(
                    Finding(
                        rule=CODE,
                        line=stmt.lineno,
                        col=stmt.col_offset,
                        message=MESSAGE,
                        severity="hard-fail",
                    )
                )
    return findings


rule = Rule(code=CODE, check=_check)
