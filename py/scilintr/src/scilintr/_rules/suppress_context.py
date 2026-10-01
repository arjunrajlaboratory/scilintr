"""suppress-context — ``with contextlib.suppress(...):``.

``suppress(...)`` is the context-manager spelling of ``try/except: pass``: it
swallows the listed exceptions with no handler block, so the
``ExceptHandler``-based silent-fallback rules cannot see it. Like
``silent-pass``, every exception type is flagged (high recall); legitimate
best-effort uses carry a waiver.
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


def _suppress_aliases(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Return (names bound to ``contextlib.suppress``, names bound to ``contextlib``).

    A bare ``suppress`` counts only when imported from ``contextlib`` — a
    project's own ``suppress()`` context manager is not an exception swallower.
    """
    func_names: set[str] = set()
    module_names = {"contextlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "contextlib":
            for alias in node.names:
                if alias.name == "suppress":
                    func_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "contextlib":
                    module_names.add(alias.asname or alias.name)
    return func_names, module_names


def _is_suppress_call(expr: ast.expr, func_names: set[str], module_names: set[str]) -> bool:
    if not isinstance(expr, ast.Call):
        return False
    func = expr.func
    if isinstance(func, ast.Name):
        return func.id in func_names
    if isinstance(func, ast.Attribute) and func.attr == "suppress":
        return isinstance(func.value, ast.Name) and func.value.id in module_names
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    func_names, module_names = _suppress_aliases(tree)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        if not any(
            _is_suppress_call(item.context_expr, func_names, module_names) for item in node.items
        ):
            continue
        # Anchor at the first statement of the block (cf. silent-pass) so a
        # waiver above the `with`, trailing it, or opening the block all fall
        # inside the forward waiver window. A parenthesised header spanning
        # several lines would push the block past a waiver above the `with`,
        # so there the `with` line itself is the anchor.
        header_end = max(
            (item.optional_vars or item.context_expr).end_lineno or node.lineno
            for item in node.items
        )
        anchor = node.body[0] if header_end == node.lineno else node
        findings.append(
            Finding(
                rule=CODE,
                line=anchor.lineno,
                col=anchor.col_offset,
                message=MESSAGE,
                severity="hard-fail",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check)
