"""return-none-on-missing-input — ``if not <path>.exists(): return None``.

This is a fallback wearing a different costume — the caller propagates ``None``
through downstream merges and the analysis silently runs on a smaller frame.

Every file-existence spelling counts: the ``.exists()`` method, ``os.path``'s
``exists`` / ``isfile`` / ``isdir`` (called through ``os.path`` or an alias, or
imported bare), and pathlib's ``is_file()`` / ``is_dir()``; guards may be
combined with other conditions by ``or`` / ``and``. The guard body may log before returning; the
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
from scilintr._rules._scope import Imports

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
    """Whether ``func`` produces values: a non-None ``return``, or any ``yield``
    (a generator's bare ``return`` ends a value stream early)."""
    for n in _own_nodes(func):
        if isinstance(n, (ast.Yield, ast.YieldFrom)):
            return True
        if (
            isinstance(n, ast.Return)
            and n.value is not None
            and not (isinstance(n.value, ast.Constant) and n.value.value is None)
        ):
            return True
    return False


def _is_placeholder_return(node: ast.AST, returns_value: bool) -> bool:
    if not isinstance(node, ast.Return) or not is_degraded_default(node.value):
        return False
    is_none = node.value is None or (isinstance(node.value, ast.Constant) and node.value.value is None)
    # A bare/None return counts only in a function that otherwise produces values.
    return returns_value or not is_none


def _degraded_return(body: list[ast.stmt], returns_value: bool) -> ast.Return | None:
    """The guard body's ``return <placeholder>`` — after any logging, possibly
    nested in further conditions (``if allow_missing: return None``) — unless
    the body raises unconditionally first."""
    for stmt in body:
        if isinstance(stmt, ast.Raise):
            return None
        if isinstance(stmt, _SCOPES):  # a nested def's returns are not this guard's
            continue
        for node in [stmt, *_own_nodes(stmt)]:
            if _is_placeholder_return(node, returns_value):
                return node
    return None


def compound(pred: Callable[[ast.expr], bool]) -> Callable[[ast.expr], bool]:
    """Lift a guard predicate over ``or`` / ``and``: the branch is a guard if any
    operand is. ``not p.exists() and allow_missing`` still runs only when the
    input is missing, and ``not p.exists() or force`` runs whenever it is."""

    def _test(test: ast.expr) -> bool:
        if isinstance(test, ast.BoolOp):
            return any(_test(v) for v in test.values)
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


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    imports = Imports(tree)

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
            return func.attr in _OS_PATH_FUNCS and imports.attr_origin(func.value) in _OS_PATH_MODULES
        if isinstance(func, ast.Name):
            origin = imports.origin(func)  # scope-aware: a parameter `isfile` is not os.path's
            return origin is not None and origin[0] in _OS_PATH_MODULES and origin[1] in _OS_PATH_FUNCS
        return False

    return [
        Finding(rule=CODE, line=r.lineno, col=r.col_offset, message=MESSAGE, severity="hard-fail")
        for r in guarded_returns(tree, compound(is_missing))
    ]


rule = Rule(code=CODE, check=_check)
