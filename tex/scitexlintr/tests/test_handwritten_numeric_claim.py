"""Rule: handwritten-numeric-claim (manifest-free)."""

from __future__ import annotations

RULE = "handwritten-numeric-claim"


def test_handwritten_flags_n_equals(has_finding, wrap_body):
    assert has_finding(wrap_body("We saw n = 23 in earlier work."), RULE)


def test_handwritten_flags_capital_n_equals(has_finding, wrap_body):
    assert has_finding(wrap_body("We saw N = 23 in earlier work."), RULE)


def test_handwritten_flags_p_equals_scientific(has_finding, wrap_body):
    assert has_finding(wrap_body("With p = 1e-8, the result was significant."), RULE)


def test_handwritten_flags_r_equals(has_finding, wrap_body):
    assert has_finding(wrap_body("We measured r = 0.82 across replicates."), RULE)


def test_handwritten_passes_long_word_prefix(has_finding, wrap_body):
    # ``mean = 23`` should NOT match — only single-letter prefixes count.
    src = wrap_body("The mean = 23 across pooled samples.")
    assert not has_finding(src, RULE)


def test_handwritten_passes_section_reference(has_finding, wrap_body):
    src = wrap_body("See Section 4.2 for the QC pipeline.")
    assert not has_finding(src, RULE)


def test_handwritten_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[handwritten-numeric-claim]: footnote citing prior work N=23\n"
        "We saw n = 23 in earlier work."
    )
    assert not has_finding(src, RULE)


def test_handwritten_runs_without_manifest(wrap_body):
    """Manifest-free rules must fire without --manifest."""
    from scitexlintr import lint_tex
    src = wrap_body("We saw n = 23 in earlier work.")
    findings = lint_tex(src, filename="t.tex", manifest=None)
    assert any(f.rule == RULE for f in findings)
