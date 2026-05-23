"""Lint engine — parses source, runs every rule, applies waivers, returns findings."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

from scilintr._finding import Finding
from scilintr._rules import ALL_CROSS_FILE_RULES, ALL_RULES
from scilintr._waivers import find_waivers, is_waived


def lint_code(
    source: str,
    *,
    filename: str = "<test>",
    rules: list[str] | None = None,
    respect_waivers: bool = True,
) -> list[Finding]:
    """Lint a single Python source string.

    ``rules`` restricts checks to the listed rule codes. ``respect_waivers=False``
    disables ``ANALYSIS_OK`` suppression — useful for audits that want to see what
    has been waivered.
    """
    tree = ast.parse(source, filename=filename)

    selected = ALL_RULES if rules is None else [r for r in ALL_RULES if r.code in rules]

    findings: list[Finding] = []
    for rule in selected:
        for f in rule.check(tree, source, filename):
            if not f.filename:
                f = replace(f, filename=filename)
            findings.append(f)

    if respect_waivers:
        waivers = find_waivers(source)
        findings = [f for f in findings if not is_waived(f.line, waivers)]

    return findings


def lint_paths(
    paths: list[str],
    *,
    rules: list[str] | None = None,
    respect_waivers: bool = True,
) -> list[Finding]:
    """Lint one or more files / directories, running both per-file and cross-file rules.

    Per-file rules execute the same way as ``lint_code``. Cross-file rules see the
    full set of parsed files at once (used by ``duplicate-parameter-source`` to
    detect a constant in one file disagreeing with a CLI default in another).
    """
    files = _resolve_python_files(paths)

    parsed: dict[str, tuple[ast.AST, str]] = {}
    findings: list[Finding] = []

    for path in files:
        try:
            source = path.read_text()
        except UnicodeDecodeError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            # Skip unparseable files — the per-file CLI handles them with a printed warning;
            # here we silently skip because batch mode doesn't have a place to surface them.
            continue
        parsed[str(path)] = (tree, source)

    # Per-file rules
    selected = ALL_RULES if rules is None else [r for r in ALL_RULES if r.code in rules]
    for filename, (tree, source) in parsed.items():
        for rule in selected:
            for f in rule.check(tree, source, filename):
                if not f.filename:
                    f = replace(f, filename=filename)
                findings.append(f)

    # Cross-file rules
    cross_selected = (
        ALL_CROSS_FILE_RULES
        if rules is None
        else [r for r in ALL_CROSS_FILE_RULES if r.code in rules]
    )
    for rule in cross_selected:
        findings.extend(rule.check_files(parsed))

    if respect_waivers:
        # Waivers are per-file. Build a per-file index and consult it via finding.filename.
        per_file_waivers = {
            filename: find_waivers(source) for filename, (_tree, source) in parsed.items()
        }

        def _is_waived(f: Finding) -> bool:
            return is_waived(f.line, per_file_waivers.get(f.filename, []))

        findings = [f for f in findings if not _is_waived(f)]

    return findings


def _resolve_python_files(paths: list[str]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        p = Path(raw)
        if p.is_file() and p.suffix == ".py":
            r = p.resolve()
            if r not in seen:
                seen.add(r)
                out.append(p)
        elif p.is_dir():
            for child in sorted(p.rglob("*.py")):
                r = child.resolve()
                if r not in seen:
                    seen.add(r)
                    out.append(child)
    return out
