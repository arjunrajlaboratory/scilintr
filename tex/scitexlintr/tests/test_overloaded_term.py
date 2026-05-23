"""Rule: overloaded-term-no-warning."""

from __future__ import annotations

RULE = "overloaded-term-no-warning"


def test_overloaded_flags_first_use_without_warning(has_finding, wrap_body):
    src = wrap_body("The BCLRT score was elevated in tumor samples.")
    assert has_finding(src, RULE)


def test_overloaded_passes_when_warning_precedes(has_finding, wrap_body):
    src = wrap_body(
        "Not a Wilks-sense LRT; threshold 10 corresponds to Wilks 20.\n"
        "The BCLRT score was elevated in tumor samples."
    )
    assert not has_finding(src, RULE)


def test_overloaded_only_fires_on_first_use(findings_for, wrap_body):
    src = wrap_body(
        "The BCLRT score was elevated in tumor samples.\n"
        "Not a Wilks-sense LRT; threshold 10 corresponds to Wilks 20.\n"
        "A later BCLRT mention should be fine."
    )
    fl = findings_for(src, RULE)
    # The second BCLRT (after the warning) must NOT fire.
    assert len(fl) == 1


def test_overloaded_passes_when_warning_in_same_sentence(has_finding, wrap_body):
    """Self-review bug: str.find searched [body_start, first_match.end()) —
    a warning that begins AFTER the first term mention in the same
    sentence was treated as absent. The disambiguation right there
    should count."""
    src = wrap_body(
        "We applied the BCLRT — Not a Wilks-sense LRT; threshold 10 corresponds to Wilks 20."
    )
    assert not has_finding(src, RULE)


def test_overloaded_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[overloaded-term-no-warning]: definition pending in methods\n"
        "The BCLRT score was elevated in tumor samples."
    )
    assert not has_finding(src, RULE)
