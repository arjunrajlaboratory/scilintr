"""return-none-on-missing-input — ``if not <path>.exists(): return None``.

This is a fallback wearing a different costume — the caller propagates ``None``
through downstream merges and the analysis silently runs on a smaller frame.

Every file-existence spelling counts: the ``.exists()`` method, ``os.path``'s
``exists`` / ``isfile`` / ``isdir`` (called through the module or imported
bare), and pathlib's ``is_file()`` / ``is_dir()``. The returned side is any
degraded placeholder (``None``, empty container, ``0``, ``NaN``) — the same
definition the silent-fallback-value rules use.

The broader "upstream already empty" guards (``is None``, ``len(x) == 0``)
live in the opt-in sibling ``return-none-on-empty-input``.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule
from scilintr._rules._degraded_default import is_degraded_default

CODE = "return-none-on-missing-input"
MESSAGE = (
    "returning None (or another placeholder) when the input file is missing silently "
    "propagates absence downstream; "
    "raise FileNotFoundError or add ANALYSIS_OK[optional-input] with justification"
)

# Method / module-function names that test whether a path exists.
_EXISTENCE_ATTRS = {"exists", "isfile", "isdir", "is_file", "is_dir"}
_OS_PATH_FUNCS = {"exists", "isfile", "isdir"}


def _os_path_imports(tree: ast.AST) -> set[str]:
    """Bare names bound by ``from os.path import exists/isfile/isdir [as x]``."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in {"os.path", "posixpath", "ntpath"}:
            for alias in node.names:
                if alias.name in _OS_PATH_FUNCS:
                    names.add(alias.asname or alias.name)
    return names


def _is_negated_exists_test(test: ast.expr, bare_names: set[str]) -> bool:
    if not isinstance(test, ast.UnaryOp) or not isinstance(test.op, ast.Not):
        return False
    inner = test.operand
    if not isinstance(inner, ast.Call):
        return False
    func = inner.func
    if isinstance(func, ast.Attribute):
        return func.attr in _EXISTENCE_ATTRS
    if isinstance(func, ast.Name):
        return func.id in bare_names
    return False


def degraded_return(body: list[ast.stmt]) -> ast.Return | None:
    """The guard body's leading ``return <placeholder>``, if it has one."""
    if body and isinstance(body[0], ast.Return) and is_degraded_default(body[0].value):
        return body[0]
    return None


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    bare_names = _os_path_imports(tree)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not _is_negated_exists_test(node.test, bare_names):
            continue
        ret = degraded_return(node.body)
        if ret is None:
            continue
        findings.append(
            Finding(
                rule=CODE,
                line=ret.lineno,
                col=ret.col_offset,
                message=MESSAGE,
                severity="hard-fail",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check)
