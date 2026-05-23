"""Tests for the ``# ANALYSIS_OK[category]:`` waiver mechanism.

The waiver suppresses any finding whose source location is within a configurable
window of lines around the comment. The category name is part of the comment for
human reviewers; the engine treats any well-formed ``ANALYSIS_OK[<word>]:`` as
authoritative (category-to-rule strictness can be added later as opt-in mode).
"""

from __future__ import annotations


def test_waiver_on_line_above_suppresses(has_finding):
    src = (
        "try:\n"
        "    pass\n"
        "# ANALYSIS_OK[api-retry]: retry on transient failure\n"
        "except Exception:\n"
        "    pass\n"
    )
    assert not has_finding(src, "broad-exception")


def test_waiver_on_same_line_suppresses(has_finding):
    src = (
        "try:\n"
        "    pass\n"
        "except Exception:  # ANALYSIS_OK[api-retry]: retry on transient failure\n"
        "    pass\n"
    )
    assert not has_finding(src, "broad-exception")


def test_waiver_too_far_away_does_not_suppress(has_finding):
    src = "# ANALYSIS_OK[api-retry]: retry on transient failure\n"
    src += "\n" * 50
    src += "try:\n    pass\nexcept Exception:\n    pass\n"
    assert has_finding(src, "broad-exception"), "waiver 50 lines away should not suppress"


def test_waiver_without_category_does_not_suppress(has_finding):
    # Generic 'ANALYSIS_OK' with no [category] is rejected per the strategy doc.
    src = (
        "# ANALYSIS_OK: this should not count\n"
        "try:\n    pass\nexcept Exception:\n    pass\n"
    )
    assert has_finding(src, "broad-exception")


def test_waiver_without_explanation_does_not_suppress(has_finding):
    # ANALYSIS_OK[category] with no trailing explanation is rejected.
    src = (
        "# ANALYSIS_OK[api-retry]\n"
        "try:\n    pass\nexcept Exception:\n    pass\n"
    )
    assert has_finding(src, "broad-exception")


def test_waiver_with_empty_explanation_does_not_suppress(has_finding):
    src = (
        "# ANALYSIS_OK[api-retry]:    \n"
        "try:\n    pass\nexcept Exception:\n    pass\n"
    )
    assert has_finding(src, "broad-exception")


def test_waiver_below_finding_does_not_suppress(has_finding):
    # A waiver after the offending code shouldn't retroactively suppress earlier findings.
    src = (
        "try:\n"
        "    pass\n"
        "except Exception:\n"
        "    pass\n"
        "# ANALYSIS_OK[api-retry]: this comment is BELOW the except handler\n"
    )
    assert has_finding(src, "broad-exception"), (
        "waiver below the finding must not suppress — semantics is forward-looking only"
    )


def test_waiver_continuation_is_recognized(has_finding):
    # A two-line waiver: the leading comment carries the category, the next
    # comment continues the explanation. Both forms should suppress.
    src = (
        "# ANALYSIS_OK[api-retry]: retry once on transient API error;\n"
        "# no alternate dataset fallback is used\n"
        "try:\n    pass\nexcept Exception:\n    pass\n"
    )
    assert not has_finding(src, "broad-exception")
