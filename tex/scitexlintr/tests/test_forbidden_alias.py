"""Rule: forbidden-alias."""

from __future__ import annotations

RULE = "forbidden-alias"


def test_forbidden_alias_flags_accuracy(has_finding, wrap_body):
    src = wrap_body(r"The accuracy was \SciVal{\ExactAccuracy}{0.973}.")
    assert has_finding(src, RULE)


def test_forbidden_alias_flags_total_cells(has_finding, wrap_body):
    src = wrap_body("There were many total cells in the cohort.")
    assert has_finding(src, RULE)


def test_forbidden_alias_passes_canonical(has_finding, wrap_body):
    src = wrap_body(r"The exact match accuracy was \SciVal{\ExactAccuracy}{0.973}.")
    assert not has_finding(src, RULE)


def test_forbidden_alias_word_boundary(has_finding, wrap_body):
    # "inaccuracy" should NOT trigger.
    src = wrap_body("Reviewers noted the inaccuracy of the old description.")
    assert not has_finding(src, RULE)


def test_forbidden_alias_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[forbidden-alias]: quoting a reviewer's exact wording\n"
        r"The accuracy was \SciVal{\ExactAccuracy}{0.973}."
    )
    assert not has_finding(src, RULE)
