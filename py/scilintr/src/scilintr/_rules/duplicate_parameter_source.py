"""duplicate-parameter-source — same parameter declared with different defaults in two places.

Looks at every ``parser.add_argument("--kebab-name", default=X)`` and every module-level
``UPPER_SNAKE = Y`` constant; if their normalized stems match and the literal default
values differ, both sites are flagged.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "duplicate-parameter-source"
MESSAGE = (
    "same parameter has different defaults in two places — pick one canonical source and "
    "have the other read from it, or add ANALYSIS_OK[duplicate-config-source]"
)


def _stem_from_option(option: str) -> str | None:
    if not option:
        return None
    return option.lstrip("-").replace("-", "_").upper()


def _stem_from_constant_name(name: str) -> str | None:
    if not name.isupper() or name.startswith("_"):
        return None
    return name


def _literal_value(node: ast.AST):
    if isinstance(node, ast.Constant):
        return ("const", node.value)
    if isinstance(node, ast.Name):
        return ("name", node.id)
    return None


def _collect_constants(tree: ast.Module) -> dict[str, tuple[int, object]]:
    """Module-level UPPER_SNAKE = <constant> assignments."""
    out: dict[str, tuple[int, object]] = {}
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        tgt = stmt.targets[0]
        if not isinstance(tgt, ast.Name):
            continue
        stem = _stem_from_constant_name(tgt.id)
        if stem is None:
            continue
        val = _literal_value(stmt.value)
        if val is not None:
            out[stem] = (stmt.lineno, val[1])
    return out


def _collect_cli_defaults(tree: ast.AST) -> list[tuple[ast.Call, str, object | None]]:
    out: list[tuple[ast.Call, str, object | None]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            continue
        option = None
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("-"):
                option = arg.value
                break
        if option is None:
            continue
        stem = _stem_from_option(option)
        if stem is None:
            continue

        default_val: object | None = None
        for kw in node.keywords:
            if kw.arg == "default":
                lit = _literal_value(kw.value)
                if lit is not None:
                    default_val = lit  # ("const", v) or ("name", id)
        out.append((node, stem, default_val))
    return out


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    if not isinstance(tree, ast.Module):
        return []
    consts = _collect_constants(tree)
    if not consts:
        return []

    findings: list[Finding] = []
    for call_node, stem, default in _collect_cli_defaults(tree):
        if stem not in consts:
            continue
        const_line, const_val = consts[stem]

        # If the CLI default IS the constant Name (single source of truth), no flag.
        if default is not None and default[0] == "name" and default[1] == stem:
            continue
        # If they're equal constants, no flag.
        if default is not None and default[0] == "const" and default[1] == const_val:
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
