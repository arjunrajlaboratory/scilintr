"""Rule: snapshot-mismatch."""

from __future__ import annotations

RULE = "snapshot-mismatch"


def test_snapshot_mismatch_flags_drifted_int(has_finding, wrap_body):
    src = wrap_body(r"We saw \SciVal{\NSamples}{47} cells.")
    assert has_finding(src, RULE)


def test_snapshot_mismatch_flags_drifted_text(has_finding, wrap_body):
    src = wrap_body(
        r"For the \SciText{\ContrastPhrase}{control versus treated} comparison."
    )
    assert has_finding(src, RULE)


def test_snapshot_mismatch_passes_matching_int(has_finding, wrap_body):
    src = wrap_body(r"We saw \SciVal{\NSamples}{48} cells.")
    assert not has_finding(src, RULE)


def test_snapshot_mismatch_passes_matching_float(has_finding, wrap_body):
    src = wrap_body(r"FDR $< \SciVal{\FDRThreshold}{0.05}$.")
    assert not has_finding(src, RULE)


def test_snapshot_mismatch_passes_matching_text(has_finding, wrap_body):
    src = wrap_body(
        r"For the \SciText{\ContrastPhrase}{treated versus control} comparison."
    )
    assert not has_finding(src, RULE)


def test_snapshot_mismatch_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[snapshot-mismatch]: snapshot intentionally pre-update for review\n"
        r"We saw \SciVal{\NSamples}{47} cells."
    )
    assert not has_finding(src, RULE)


def test_snapshot_mismatch_carries_fix(lint, wrap_body):
    src = wrap_body(r"We saw \SciVal{\NSamples}{47} cells.")
    findings = [f for f in lint(src) if f.rule == RULE]
    assert findings and findings[0].fix is not None
    assert findings[0].fix.replacement == "48"
