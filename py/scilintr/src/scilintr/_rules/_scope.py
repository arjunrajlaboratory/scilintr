"""Scope-aware resolution of imported names.

A rule that asks "is this ``suppress`` the stdlib ``contextlib.suppress``?"
must respect Python's scoping: an import inside one function says nothing
about a same-named parameter, local, or import in another, and a later
rebinding shadows an earlier import. ``Imports(tree).origin(name_node)``
walks the enclosing scopes outward (function → … → module, skipping class
bodies as Python does) and returns what the name was bound to by its most
recent binding at or before the use — or ``None`` when that binding is not
an absolute import (a parameter, assignment, ``def``, relative import) or
the name is unbound.

``origin`` is ``(module, attr)``: ``import contextlib as cl`` binds ``cl`` to
``("contextlib", None)``; ``from contextlib import suppress as s`` binds ``s``
to ``("contextlib", "suppress")``; ``import os.path`` binds ``os`` to
``("os", None)``; ``import os.path as osp`` binds ``osp`` to
``("os.path", None)``.
"""

from __future__ import annotations

import ast

Origin = tuple[str, str | None]

_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
_SCOPES = (*_FUNCS, ast.ClassDef, ast.Module)


class Imports:
    def __init__(self, tree: ast.AST) -> None:
        self._parent: dict[int, ast.AST] = {}
        # scope id -> name -> [(lineno, origin | None)], in source order
        self._bindings: dict[int, dict[str, list[tuple[int, Origin | None]]]] = {}
        self._index(tree)

    # ---- public -------------------------------------------------------

    def origin(self, node: ast.Name) -> Origin | None:
        scope = self._scope_of(node)
        first = True
        while scope is not None:
            # Class bodies are not enclosing scopes for nested functions.
            if first or not isinstance(scope, ast.ClassDef):
                found = self._lookup(scope, node.id, node.lineno)
                if found is not _UNBOUND:
                    return found
            first = False
            scope = self._scope_of(scope)
        return None

    def attr_origin(self, node: ast.expr) -> str | None:
        """Dotted module a ``Name``/``Attribute`` chain refers to, e.g. ``"os.path"``
        for ``os.path`` (with ``import os``) or ``osp`` (with ``import os.path as osp``)."""
        if isinstance(node, ast.Name):
            o = self.origin(node)
            if o is None:
                return None
            module, attr = o
            return f"{module}.{attr}" if attr else module
        if isinstance(node, ast.Attribute):
            base = self.attr_origin(node.value)
            return f"{base}.{node.attr}" if base else None
        return None

    # ---- internals ----------------------------------------------------

    def _lookup(self, scope: ast.AST, name: str, line: int):
        entries = self._bindings.get(id(scope), {}).get(name)
        if not entries:
            return _UNBOUND
        before = [o for ln, o in entries if ln <= line]
        # A function body runs after the whole module is bound, so a use in a
        # nested scope may see a later module-level binding; fall back to the last.
        return before[-1] if before else entries[-1][1]

    def _scope_of(self, node: ast.AST) -> ast.AST | None:
        p = self._parent.get(id(node))
        while p is not None and not isinstance(p, _SCOPES):
            p = self._parent.get(id(p))
        return p

    def _bind(self, scope: ast.AST, name: str, line: int, origin: Origin | None) -> None:
        self._bindings.setdefault(id(scope), {}).setdefault(name, []).append((line, origin))

    def _index(self, tree: ast.AST) -> None:
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                self._parent[id(child)] = parent
        for node in ast.walk(tree):
            scope = self._scope_of(node)
            if scope is None:
                continue
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.asname:
                        self._bind(scope, a.asname, node.lineno, (a.name, None))
                    else:
                        top = a.name.split(".")[0]
                        self._bind(scope, top, node.lineno, (top, None))
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    origin = (node.module, a.name) if node.level == 0 and node.module else None
                    self._bind(scope, a.asname or a.name, node.lineno, origin)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                self._bind(scope, node.id, node.lineno, None)
            elif isinstance(node, (*_FUNCS[:2], ast.ClassDef)):
                self._bind(scope, node.name, node.lineno, None)
            elif isinstance(node, ast.arg):
                # `scope` is the function the parameter belongs to.
                self._bind(scope, node.arg, scope.lineno, None)

_UNBOUND = object()
