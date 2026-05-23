"""Rule: raw-generated-value."""

from __future__ import annotations

RULE = "raw-generated-value"


def test_raw_value_flags_bare_int_in_prose(has_finding, wrap_body):
    src = wrap_body("The 317 differentially expressed genes cluster into three groups.")
    assert has_finding(src, RULE)


def test_raw_value_flags_bare_phrase_in_prose(has_finding, wrap_body):
    src = wrap_body("We focused on treated versus control comparisons across batches.")
    assert has_finding(src, RULE)


def test_raw_value_passes_wrapped_int(has_finding, wrap_body):
    src = wrap_body(r"We observed \SciVal{\NDEGenes}{317} DE genes overall.")
    assert not has_finding(src, RULE)


def test_raw_value_passes_wrapped_text(has_finding, wrap_body):
    src = wrap_body(r"For \SciText{\ContrastPhrase}{treated versus control}, we ...")
    assert not has_finding(src, RULE)


def test_raw_value_word_boundary(has_finding, wrap_body):
    # 3175 should NOT match 317 (word boundary on the right).
    src = wrap_body("A neighboring transcript locus 3175 was excluded.")
    assert not has_finding(src, RULE)


def test_raw_value_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[raw-generated-value]: this 317 refers to the prior dataset\n"
        "The 317 differentially expressed genes cluster into three groups."
    )
    assert not has_finding(src, RULE)
