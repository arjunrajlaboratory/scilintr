"""Cross-file extension of ``duplicate-parameter-source``.

Catches the case where the same parameter has one default in a module-level
``UPPER_SNAKE`` constant and a different default in a sibling script's
``add_argument(..., default=...)``. Each script in isolation looks fine;
together they're not.

This rule pairs with the per-file ``duplicate-parameter-source`` and shares
its rule code so users see one category. Within-file conflicts are caught by
the per-file rule; cross-file conflicts are caught here.
"""

from __future__ import annotations

import ast
import os
from collections import defaultdict

from scilintr._finding import Finding
from scilintr._rules._base import CrossFileRule

CODE = "duplicate-parameter-source"
MESSAGE_TEMPLATE = (
    "{stem} has different defaults across files: {sites} — pick one canonical "
    "source and import it everywhere, or add ANALYSIS_OK[duplicate-config-source]"
)


def _stem_from_option(option: str) -> str | None:
    if not option:
        return None
    return option.lstrip("-").replace("-", "_").upper()


def _literal_value(node: ast.AST):
    if isinstance(node, ast.Constant):
        return ("const", node.value)
    if isinstance(node, ast.Name):
        return ("name", node.id)
    return None


def _collect_constants(tree: ast.AST) -> list[tuple[str, int, tuple]]:
    """Module-level UPPER_SNAKE = <literal> assignments."""
    out: list[tuple[str, int, tuple]] = []
    if not isinstance(tree, ast.Module):
        return out
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        tgt = stmt.targets[0]
        if not isinstance(tgt, ast.Name):
            continue
        if not tgt.id.isupper() or tgt.id.startswith("_"):
            continue
        val = _literal_value(stmt.value)
        if val is None:
            continue
        out.append((tgt.id, stmt.lineno, val))
    return out


def _collect_cli_defaults(tree: ast.AST) -> list[tuple[str, int, tuple]]:
    out: list[tuple[str, int, tuple]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            continue
        option = None
        for arg in node.args:
            if (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, str)
                and arg.value.startswith("-")
            ):
                option = arg.value
                break
        if option is None:
            continue
        stem = _stem_from_option(option)
        if stem is None:
            continue
        default_val = None
        for kw in node.keywords:
            if kw.arg == "default":
                default_val = _literal_value(kw.value)
        if default_val is None:
            continue
        out.append((stem, node.lineno, default_val))
    return out


def _check_files(parsed: dict[str, tuple[ast.AST, str]]) -> list[Finding]:
    # A constant/CLI default is only a shared source of truth among files that
    # live in the same analysis directory. Two independent analyses that reuse a
    # generic name (TOP_N, N_NULL, SEED, …) with different values have nothing to
    # reconcile, so compare only within a directory boundary (issue #5).
    by_dir: dict[str, dict[str, tuple[ast.AST, str]]] = defaultdict(dict)
    for filename, parsed_file in parsed.items():
        by_dir[os.path.dirname(filename)][filename] = parsed_file

    findings: list[Finding] = []
    for group in by_dir.values():
        findings.extend(_check_group(group))
    return findings


def _check_group(parsed: dict[str, tuple[ast.AST, str]]) -> list[Finding]:
    # Aggregate: stem -> list[(filename, line, value)]
    sources: dict[str, list[tuple[str, int, tuple]]] = defaultdict(list)
    for filename, (tree, _source) in parsed.items():
        for stem, line, val in _collect_constants(tree):
            sources[stem].append((filename, line, val))
        for stem, line, val in _collect_cli_defaults(tree):
            sources[stem].append((filename, line, val))

    findings: list[Finding] = []
    for stem, sites in sources.items():
        if len(sites) < 2:
            continue
        files = {s[0] for s in sites}
        if len(files) < 2:
            # Within-file conflicts are the per-file rule's job.
            continue
        const_values = {s[2][1] for s in sites if s[2][0] == "const"}
        if len(const_values) <= 1:
            # All literal values agree (or only Name references exist) — no conflict.
            continue

        site_summary = ", ".join(
            f"{_basename(fn)}:{ln} ({_render_value(val)})" for fn, ln, val in sites
        )
        msg = MESSAGE_TEMPLATE.format(stem=stem, sites=site_summary)

        # Emit one finding per conflict, anchored at the most operative site. Order of
        # preference: an argparse default (a CLI flag is what users invoke), otherwise
        # the alphabetically-first file (deterministic). This means a waiver in the
        # anchored file suppresses the whole conflict cleanly.
        anchor = sorted(sites, key=lambda s: (0 if s[2][0] == "const" else -1, s[0], s[1]))[-1]
        findings.append(
            Finding(
                rule=CODE,
                line=anchor[1],
                col=0,
                message=msg,
                severity="structured-comment",
                filename=anchor[0],
            )
        )
    return findings


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _render_value(val: tuple) -> str:
    kind, payload = val
    if kind == "const":
        return repr(payload)
    return f"<-{payload}"


rule = CrossFileRule(code=CODE, check_files=_check_files)
