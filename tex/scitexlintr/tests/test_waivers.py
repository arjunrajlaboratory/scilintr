"""Tests for the TeX waiver mechanism."""

from __future__ import annotations

from scitexlintr._waivers import find_waivers, is_waived


def test_waiver_well_formed():
    src = "% ANALYSIS_OK[snapshot-mismatch]: this snapshot is intentionally stale\n"
    ws = find_waivers(src)
    assert len(ws) == 1
    assert ws[0].category == "snapshot-mismatch"
    assert "stale" in ws[0].explanation


def test_waiver_bare_token_is_rejected():
    src = "% ANALYSIS_OK\n"
    assert find_waivers(src) == []


def test_waiver_missing_explanation_is_rejected():
    src = "% ANALYSIS_OK[snapshot-mismatch]:\n"
    assert find_waivers(src) == []


def test_waiver_escaped_percent_is_not_a_waiver():
    src = r"This 50\% ANALYSIS_OK[anything]: not really a comment"
    assert find_waivers(src) == []


def test_waiver_forward_window():
    src = (
        "% ANALYSIS_OK[snapshot-mismatch]: explanatory text here\n"
        "line2\n"
        "line3\n"
        "line4\n"
        "line5\n"
        "line6\n"
    )
    ws = find_waivers(src)
    assert is_waived(2, "snapshot-mismatch", ws)
    assert is_waived(5, "snapshot-mismatch", ws)  # within window
    assert not is_waived(6, "snapshot-mismatch", ws)  # past window


def test_waiver_does_not_cross_rule_codes():
    src = "% ANALYSIS_OK[snapshot-mismatch]: comment\n"
    ws = find_waivers(src)
    assert is_waived(1, "snapshot-mismatch", ws)
    assert not is_waived(1, "raw-generated-value", ws)
