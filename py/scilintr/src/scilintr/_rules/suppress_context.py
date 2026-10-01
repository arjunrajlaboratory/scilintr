"""suppress-context — ``contextlib.suppress(...)``.

``suppress(...)`` is the context-manager spelling of ``try/except: pass``: it
swallows the listed exceptions with no handler block, so the
``ExceptHandler``-based silent-fallback rules cannot see it. Like
``silent-pass``, every exception type is flagged (high recall); legitimate
best-effort uses carry a waiver.

Every call is flagged, wherever it appears: as a ``with`` item, entered
through ``ExitStack.enter_context(...)``, or bound to a name for later use.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule
from scilintr._rules._scope import Imports

CODE = "suppress-context"
MESSAGE = (
    "`contextlib.suppress` swallows exceptions with no log or recovery — the `silent-pass` "
    "costume as a context manager; narrow + handle the exception, or add "
    "ANALYSIS_OK[best-effort] with justification"
)


def _is_suppress_call(expr: ast.AST, imports: Imports) -> bool:
    """A call resolving — through the enclosing scopes — to ``contextlib.suppress``.

    A project's own ``suppress()``, a third-party or relative ``contextlib``, a
    parameter or a rebinding named ``suppress`` is not the stdlib swallower."""
    if not isinstance(expr, ast.Call):
        return False
    func = expr.func
    if isinstance(func, ast.Name):
        return imports.origin(func) == ("contextlib", "suppress")
    if isinstance(func, ast.Attribute) and func.attr == "suppress":
        return imports.attr_origin(func.value) == "contextlib"
    return False


def _finding(line: int, col: int, waiver_end: int | None = None) -> Finding:
    return Finding(
        rule=CODE, line=line, col=col, message=MESSAGE, severity="hard-fail", waiver_end=waiver_end
    )


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    nodes = list(ast.walk(tree))
    imports = Imports(tree)
    calls = [n for n in nodes if _is_suppress_call(n, imports)]
    if not calls:
        return []
    findings: list[Finding] = []
    in_with: set[int] = set()
    for node in nodes:
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        items = [i.context_expr for i in node.items if i.context_expr in calls]
        if not items:
            continue
        in_with.update(id(c) for c in items)
        # Reported on the `with` line; a waiver above it, trailing any header
        # line, or opening the block (up to its first statement) applies.
        findings.append(_finding(node.lineno, node.col_offset, waiver_end=node.body[0].lineno))
    for call in calls:
        if id(call) not in in_with:
            findings.append(_finding(call.lineno, call.col_offset))
    return findings


rule = Rule(code=CODE, check=_check)
