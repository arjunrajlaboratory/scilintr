"""Rule: unsourced-numeric-token (and its many context heuristics)."""

from __future__ import annotations

RULE = "unsourced-numeric-token"


def test_unsourced_flags_isolated_number(has_finding, wrap_body):
    src = wrap_body("The coverage was 99.9 across runs.")
    assert has_finding(src, RULE)


def test_unsourced_passes_manifest_value(has_finding, wrap_body):
    # 317 IS in the manifest; raw-generated-value fires instead.
    src = wrap_body("The 317 differentially expressed genes cluster.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_section_reference(has_finding, wrap_body):
    src = wrap_body("See Section 4.2 for the QC pipeline.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_figure_reference(has_finding, wrap_body):
    src = wrap_body("See Figure 3 for the volcano plot.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_percentage(has_finding, wrap_body):
    src = wrap_body(r"We recovered roughly 50\% of the input reads.")
    assert not has_finding(src, RULE)


def test_unsourced_flags_spelled_out_percent(has_finding, wrap_body):
    # Spelled-out percent IS a result claim; the typographic form is not.
    src = wrap_body("Coverage exceeded 99 percent across runs.")
    assert has_finding(src, RULE)


def test_unsourced_passes_threshold_context(has_finding, wrap_body):
    # Threshold context is owned by unwrapped-threshold / magic-tex-threshold.
    src = wrap_body(r"Using a relaxed cutoff $< 0.01$.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_handwritten_context(has_finding, wrap_body):
    # handwritten-numeric-claim owns ``n = 23`` etc.
    src = wrap_body("We saw n = 23 in earlier work.")
    assert not has_finding(src, RULE)


def test_unsourced_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[unsourced-numeric-token]: legacy QC threshold from upstream\n"
        "The coverage was 99.9 across runs."
    )
    assert not has_finding(src, RULE)
