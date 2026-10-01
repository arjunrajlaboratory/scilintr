"""return-none-on-missing-input — ``if not <path>.exists(): return None``.

This is a fallback wearing a different costume — the caller propagates ``None``
through downstream merges and the analysis silently runs on a smaller frame.

Every file-existence spelling counts: the ``.exists()`` method, ``os.path``'s
``exists`` / ``isfile`` / ``isdir`` (called through ``os.path`` or an alias, or
imported bare), and pathlib's ``is_file()`` / ``is_dir()``; guards may be
combined with ``or`` / ``and``. The guard body may log before returning; the
returned side is any degraded placeholder (``None``, empty container, ``0``,
``NaN``) — the same definition the silent-fallback-value rules use. A bare
``return`` only counts in a function that otherwise returns a value: an
early-exit procedure hands no placeholder to its caller.

The broader "upstream already empty" guards (``is None``, ``len(x) == 0``)
live in the opt-in sibling ``return-none-on-empty-input``.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator

from scilintr._finding import Finding
from scilintr._rules._base import Rule
from scilintr._rules._degraded_default import is_degraded_default

CODE = "return-none-on-missing-input"
MESSAGE = (
    "returning None (or another placeholder) when the input file is missing silently "
    "propagates absence downstream; "
    "raise FileNotFoundError or add ANALYSIS_OK[optional-input] with justification"
)

_PATHLIB_ATTRS = {"exists", "is_file", "is_dir"}
_OS_PATH_FUNCS = {"exists", "isfile", "isdir"}
_OS_PATH_MODULES = {"os.path", "posixpath", "ntpath"}

_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def _own_nodes(func: ast.AST) -> Iterator[ast.AST]:
    """Nodes inside ``func``, not descending into nested functions/classes."""
    stack = list(ast.iter_child_nodes(func))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, _SCOPES):
            stack.extend(ast.iter_child_nodes(node))


def _returns_value(func: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Return)
        and n.value is not None
        and not (isinstance(n.value, ast.Constant) and n.value.value is None)
        for n in _own_nodes(func)
    )


def _degraded_return(body: list[ast.stmt], returns_value: bool) -> ast.Return | None:
    """The guard body's ``return <placeholder>`` (after any logging), unless the
    body raises. A bare/None return counts only if the function returns values."""
    if any(isinstance(s, ast.Raise) for s in body):
        return None
    for stmt in body:
        if isinstance(stmt, ast.Return) and is_degraded_default(stmt.value):
            is_none = stmt.value is None or (
                isinstance(stmt.value, ast.Constant) and stmt.value.value is None
            )
            if is_none and not returns_value:
                return None
            return stmt
    return None


def compound(pred: Callable[[ast.expr], bool]) -> Callable[[ast.expr], bool]:
    """Lift a guard predicate over ``or`` (any operand) and ``and`` (every operand)."""

    def _test(test: ast.expr) -> bool:
        if isinstance(test, ast.BoolOp):
            parts = [_test(v) for v in test.values]
            return any(parts) if isinstance(test.op, ast.Or) else all(parts)
        return pred(test)

    return _test


def guarded_returns(tree: ast.AST, is_guard: Callable[[ast.expr], bool]) -> list[ast.Return]:
    """Every ``if <guard>: … return <placeholder>`` inside a function."""
    found: list[ast.Return] = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        returns_value = _returns_value(func)
        for node in _own_nodes(func):
            if isinstance(node, ast.If) and is_guard(node.test):
                ret = _degraded_return(node.body, returns_value)
                if ret is not None:
                    found.append(ret)
    return found


def _os_path_bindings(tree: ast.AST) -> tuple[set[str], set[str]]:
    """(bare names bound to os.path exists/isfile/isdir, names bound to the os.path module)."""
    funcs: set[str] = set()
    modules: set[str] = {"posixpath", "ntpath"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            if node.module in _OS_PATH_MODULES:
                funcs.update(a.asname or a.name for a in node.names if a.name in _OS_PATH_FUNCS)
            elif node.module == "os":
                modules.update(a.asname or a.name for a in node.names if a.name == "path")
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name in _OS_PATH_MODULES and a.asname:
                    modules.add(a.asname)
    return funcs, modules


def _is_os_path(expr: ast.expr, modules: set[str]) -> bool:
    if isinstance(expr, ast.Name):
        return expr.id in modules
    return (
        isinstance(expr, ast.Attribute)
        and expr.attr == "path"
        and isinstance(expr.value, ast.Name)
        and expr.value.id == "os"
    )


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    funcs, modules = _os_path_bindings(tree)

    def is_missing(test: ast.expr) -> bool:
        if not isinstance(test, ast.UnaryOp) or not isinstance(test.op, ast.Not):
            return False
        call = test.operand
        if not isinstance(call, ast.Call):
            return False
        func = call.func
        if isinstance(func, ast.Attribute):
            if func.attr in _PATHLIB_ATTRS:  # p.exists(), os.path.exists(p), p.is_file()
                return True
            # isfile/isdir only through os.path — TarInfo.isfile() is a type check.
            return func.attr in _OS_PATH_FUNCS and _is_os_path(func.value, modules)
        return isinstance(func, ast.Name) and func.id in funcs

    return [
        Finding(rule=CODE, line=r.lineno, col=r.col_offset, message=MESSAGE, severity="hard-fail")
        for r in guarded_returns(tree, compound(is_missing))
    ]


rule = Rule(code=CODE, check=_check)
