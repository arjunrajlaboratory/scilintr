"""Shared test helpers.

Every rule has three tests:

* ``test_<rule>_flags_bad_code`` — bad code produces at least one finding for the rule.
* ``test_<rule>_passes_good_code`` — equivalent good code produces zero findings.
* ``test_<rule>_respects_waiver`` — bad code preceded by ``# ANALYSIS_OK[<category>]:``
  produces zero findings.

The waiver test only becomes meaningful once the rule detects the pattern;
before then it passes vacuously. That's the natural TDD inflection inside each rule:
implement detection → bad-code test passes, waiver test fails →
add waiver suppression → all three pass.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from scilintr import Finding, lint_code


@pytest.fixture
def lint() -> Callable[..., list[Finding]]:
    def _lint(source: str, *, filename: str = "test.py", **kwargs) -> list[Finding]:
        return lint_code(source, filename=filename, **kwargs)

    return _lint


@pytest.fixture
def has_finding() -> Callable[..., bool]:
    def _has_finding(source: str, rule: str, *, filename: str = "test.py") -> bool:
        return any(f.rule == rule for f in lint_code(source, filename=filename))

    return _has_finding


@pytest.fixture
def findings_for() -> Callable[..., list[Finding]]:
    def _findings_for(source: str, rule: str, *, filename: str = "test.py") -> list[Finding]:
        return [f for f in lint_code(source, filename=filename) if f.rule == rule]

    return _findings_for
