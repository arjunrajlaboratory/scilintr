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
    source = p.read_text(encoding="utf-8")
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

    Fixes are skipped (left unapplied, the finding stands) when:

    * the [start, end) range contains a TeX comment (unescaped ``%``) —
      the offsets came from the stripped source, so a naive rewrite would
      erase the author's note;
    * two fixes overlap — the second cannot trust the first's offsets.
    """
    fixes = [f.fix for f in findings if f.fix is not None]
    if not fixes:
        return source, 0
    # Sort descending by start so we don't shift offsets while rewriting.
    fixes_sorted = sorted(fixes, key=lambda fx: fx.start, reverse=True)
    buf = source
    applied = 0
    last_start: int | None = None
    for fx in fixes_sorted:
        # Overlap guard: applying in descending order, each fix's end must
        # be ≤ the previous fix's start.
        if last_start is not None and fx.end > last_start:
            continue
        # Comment guard: if the byte range contains an unescaped ``%``,
        # rewriting it would erase a comment.
        if _contains_unescaped_percent(buf, fx.start, fx.end):
            continue
        buf = buf[: fx.start] + fx.replacement + buf[fx.end :]
        last_start = fx.start
        applied += 1
    return buf, applied


def _contains_unescaped_percent(s: str, start: int, end: int) -> bool:
    """Mirrors the comment-detection rule in strip_comments: a ``%`` starts
    a comment unless preceded by an odd number of backslashes."""
    i = start
    while i < end:
        if s[i] == "%":
            bs = 0
            j = i - 1
            while j >= 0 and s[j] == "\\":
                bs += 1
                j -= 1
            if bs % 2 == 0:
                return True
        i += 1
    return False
