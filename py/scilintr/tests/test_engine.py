"""Engine-level contract tests independent of any particular rule."""

from __future__ import annotations

import pytest

from scilintr import Finding, lint_code


def test_lint_code_returns_list_of_findings():
    out = lint_code("x = 1\n")
    assert isinstance(out, list)
    for f in out:
        assert isinstance(f, Finding)


def test_finding_carries_line_and_rule(has_finding, findings_for):
    # Use a broad-exception trigger because that rule has a simple, unambiguous AST shape.
    src = "try:\n    pass\nexcept Exception:\n    pass\n"
    findings = findings_for(src, "broad-exception")
    assert findings, "expected a broad-exception finding"
    assert findings[0].line == 3, f"expected line 3, got {findings[0].line}"
    assert findings[0].rule == "broad-exception"
    assert findings[0].severity in {"hard-fail", "structured-comment", "warning"}


def test_disabling_waivers_resurfaces_findings(lint):
    src = (
        "# ANALYSIS_OK[api-retry]: explanation here\n"
        "try:\n"
        "    pass\n"
        "except Exception:\n"
        "    pass\n"
    )
    suppressed = [f for f in lint(src) if f.rule == "broad-exception"]
    raw = [f for f in lint(src, respect_waivers=False) if f.rule == "broad-exception"]
    assert not suppressed, "waiver should suppress finding by default"
    assert raw, "respect_waivers=False should resurface the finding"


def test_lint_code_propagates_syntax_error():
    # Library callers see SyntaxError directly; the CLI catches it and continues.
    with pytest.raises(SyntaxError):
        lint_code("def f(:\n    pass\n")


def test_rules_filter_restricts_output(lint):
    src = (
        "try:\n"
        "    pass\n"
        "except Exception:\n"
        "    pass\n"
        "\n"
        "import warnings\n"
        "warnings.filterwarnings('ignore')\n"
    )
    only_exc = lint(src, rules=["broad-exception"])
    assert only_exc, "expected at least one broad-exception finding"
    assert all(f.rule == "broad-exception" for f in only_exc)
