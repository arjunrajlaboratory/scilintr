"""Lint engine — preprocess once, run every rule, apply waivers, apply fixes."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scitexlintr._doc import prepare
from scitexlintr._finding import Finding
from scitexlintr._manifest import Manifest, load_manifest
from scitexlintr._rules import ALL_RULES
from scitexlintr._waivers import find_waivers, is_waived


def lint_tex(
    source: str,
    *,
    filename: str = "<test>",
    manifest: Manifest | None = None,
    rules: list[str] | None = None,
    respect_waivers: bool = True,
) -> list[Finding]:
    """Lint a single TeX source string against an optional manifest."""
    doc = prepare(source, filename=filename)
    selected = ALL_RULES if rules is None else [r for r in ALL_RULES if r.code in rules]

    findings: list[Finding] = []
    for rule in selected:
        if rule.requires_manifest and manifest is None:
            continue
        for f in rule.check(doc, manifest):
            if not f.filename:
                f = replace(f, filename=filename)
            findings.append(f)

    if respect_waivers:
        waivers = find_waivers(source)
        findings = [f for f in findings if not is_waived(f.line, f.rule, waivers)]

    findings.sort(key=lambda f: (f.line, f.col, f.rule))
    return findings


def lint_file(
    path: str | Path,
    *,
    manifest_path: str | Path | None = None,
    rules: list[str] | None = None,
    respect_waivers: bool = True,
) -> list[Finding]:
    p = Path(path)
    source = p.read_text()
    manifest = load_manifest(manifest_path) if manifest_path else None
    return lint_tex(
        source,
        filename=str(p),
        manifest=manifest,
        rules=rules,
        respect_waivers=respect_waivers,
    )


def apply_fixes(source: str, findings: list[Finding]) -> tuple[str, int]:
    """Apply ``--write`` auto-fixes for findings that carry a ``Fix``.

    Fixes are applied from end-of-document to start so earlier offsets stay
    valid. Returns the rewritten source and the number of fixes applied.
    Findings without a fix are ignored.
    """
    fixes = [f.fix for f in findings if f.fix is not None]
    if not fixes:
        return source, 0
    # Sort descending by start so we don't shift offsets while rewriting.
    fixes_sorted = sorted(fixes, key=lambda fx: fx.start, reverse=True)
    buf = source
    for fx in fixes_sorted:
        buf = buf[: fx.start] + fx.replacement + buf[fx.end :]
    return buf, len(fixes_sorted)
