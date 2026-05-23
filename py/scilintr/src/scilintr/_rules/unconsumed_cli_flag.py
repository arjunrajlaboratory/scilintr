"""unconsumed-cli-flag — argparse flag declared but the parsed attribute is never read.

Walks ``add_argument(...)`` calls, computes their default destination attribute name,
then checks whether *any* attribute access in the module reads that name. If not,
the flag is dead code — the value reaches ``args`` and is dropped on the floor.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unconsumed-cli-flag"
MESSAGE = (
    "CLI flag declared but its parsed attribute is never referenced — either consume it or "
    "add ANALYSIS_OK[deprecated-flag] explaining why the flag is kept"
)


def _default_dest(option: str) -> str | None:
    """Compute the destination attribute name argparse will assign for an option string.

    For ``--foo-bar`` returns ``"foo_bar"``. For positional ``"foo"`` returns ``"foo"``.
    Returns ``None`` for things that don't look like option strings.
    """
    if not isinstance(option, str) or not option:
        return None
    stripped = option.lstrip("-")
    if not stripped:
        return None
    return stripped.replace("-", "_")


def _collect_declared_flags(tree: ast.AST) -> list[tuple[ast.Call, str]]:
    """Return list of (add_argument call node, destination name)."""
    declared: list[tuple[ast.Call, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"):
            continue

        # explicit dest= overrides
        explicit = None
        for kw in node.keywords:
            if kw.arg == "dest" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                explicit = kw.value.value
        if explicit:
            declared.append((node, explicit))
            continue

        # otherwise use the first positional that looks like a flag option
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                dest = _default_dest(arg.value)
                if dest:
                    declared.append((node, dest))
                    break

    return declared


def _find_args_names(tree: ast.AST) -> set[str]:
    """Find all variables assigned from a ``*.parse_args()`` call."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        if not (
            isinstance(val, ast.Call)
            and isinstance(val.func, ast.Attribute)
            and val.func.attr == "parse_args"
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _collect_read_attrs(tree: ast.AST, args_names: set[str]) -> set[str]:
    """Collect attribute names read off the parsed-args object(s) specifically.

    `obj.verbose` is *not* counted unless `obj` is one of the known args names —
    that prevents a stray `logger.verbose` from masking a declared-but-unused
    ``--verbose`` flag.
    """
    reads: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in args_names
        ):
            reads.add(node.attr)
        # getattr(args, "foo")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in args_names
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ):
            reads.add(node.args[1].value)
    return reads


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    declared = _collect_declared_flags(tree)
    if not declared:
        return []
    args_names = _find_args_names(tree)
    if not args_names:
        # Without a parse_args() anchor we can't tell what's consumed; skip the file.
        return []
    reads = _collect_read_attrs(tree, args_names)

    findings: list[Finding] = []
    for call_node, dest in declared:
        if dest in reads:
            continue
        findings.append(
            Finding(
                rule=CODE,
                line=call_node.lineno,
                col=call_node.col_offset,
                message=MESSAGE,
                severity="structured-comment",
            )
        )
    return findings


rule = Rule(code=CODE, check=_check)
