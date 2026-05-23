"""Rule: warning-suppression — global ``warnings.filterwarnings('ignore')`` without a narrow category."""

from __future__ import annotations

RULE = "warning-suppression"

BAD = """
import warnings
warnings.filterwarnings("ignore")
"""

GOOD = """
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib.font_manager")
"""

WAIVED = """
import warnings
# ANALYSIS_OK[warning-suppression]: matplotlib font warning is noisy on this host; data/model warnings are not suppressed
warnings.filterwarnings("ignore")
"""


def test_warning_suppression_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_warning_suppression_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_warning_suppression_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
