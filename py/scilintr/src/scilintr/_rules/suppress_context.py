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

CODE = "suppress-context"
MESSAGE = (
    "`contextlib.suppress` swallows exceptions with no log or recovery — the `silent-pass` "
    "costume as a context manager; narrow + handle the exception, or add "
    "ANALYSIS_OK[best-effort] with justification"
)


def _suppress_aliases(nodes: list[ast.AST]) -> tuple[set[str], set[str]]:
    """Return (names bound to ``contextlib.suppress``, names bound to ``contextlib``).

    A bare ``suppress`` counts only when imported from the stdlib ``contextlib``
    — a project's own ``suppress()`` (or a relative ``.contextlib``) is not an
    exception swallower.
    """
    func_names: set[str] = set()
    module_names = {"contextlib"}
    for node in nodes:
        if isinstance(node, ast.ImportFrom) and node.module == "contextlib" and node.level == 0:
            for alias in node.names:
                if alias.name == "suppress":
                    func_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "contextlib":
                    module_names.add(alias.asname or alias.name)
    return func_names, module_names


def _is_suppress_call(expr: ast.AST, func_names: set[str], module_names: set[str]) -> bool:
    if not isinstance(expr, ast.Call):
        return False
    func = expr.func
    if isinstance(func, ast.Name):
        return func.id in func_names
    if isinstance(func, ast.Attribute) and func.attr == "suppress":
        return isinstance(func.value, ast.Name) and func.value.id in module_names
    return False


def _finding(line: int, col: int, waiver_end: int | None = None) -> Finding:
    return Finding(
        rule=CODE, line=line, col=col, message=MESSAGE, severity="hard-fail", waiver_end=waiver_end
    )


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    nodes = list(ast.walk(tree))
    func_names, module_names = _suppress_aliases(nodes)
    calls = [n for n in nodes if _is_suppress_call(n, func_names, module_names)]
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
