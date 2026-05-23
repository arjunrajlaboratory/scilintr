"""Tests for ``apply_fixes`` — the engine of ``--write``."""

from __future__ import annotations

from scitexlintr import apply_fixes, lint_tex


PREAMBLE = (
    "\\documentclass{article}\n"
    "\\newcommand{\\SciVal}[2]{#1}\n"
    "\\newcommand{\\NSamples}{48}\n"
    "\\begin{document}\n"
)
POSTAMBLE = "\n\\end{document}\n"


def _wrap(body: str) -> str:
    return PREAMBLE + body + POSTAMBLE


def test_apply_fixes_rewrites_stale_snapshot(manifest):
    src = _wrap(r"We saw \SciVal{\NSamples}{47} cells.")
    findings = lint_tex(src, manifest=manifest)
    new_src, n = apply_fixes(src, findings)
    assert n == 1
    assert r"\SciVal{\NSamples}{48}" in new_src
    assert r"\SciVal{\NSamples}{47}" not in new_src


def test_apply_fixes_handles_multiple_in_one_pass(manifest):
    src = _wrap(
        r"First \SciVal{\NSamples}{47}. Second \SciVal{\NSamples}{99}."
    )
    findings = lint_tex(src, manifest=manifest)
    new_src, n = apply_fixes(src, findings)
    assert n == 2
    assert new_src.count(r"\SciVal{\NSamples}{48}") == 2


def test_apply_fixes_idempotent_on_correct_snapshot(manifest):
    src = _wrap(r"We saw \SciVal{\NSamples}{48} cells.")
    findings = lint_tex(src, manifest=manifest)
    new_src, n = apply_fixes(src, findings)
    assert n == 0
    assert new_src == src
