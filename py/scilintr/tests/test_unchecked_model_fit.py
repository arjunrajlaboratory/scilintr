"""Rule: unchecked-model-fit — iterative solver ``.fit()`` without a convergence check."""

from __future__ import annotations

RULE = "unchecked-model-fit"

BAD = """
from sklearn.linear_model import LogisticRegression
model = LogisticRegression(max_iter=100)
model.fit(X, y)
"""

GOOD = """
from sklearn.linear_model import LogisticRegression
model = LogisticRegression(max_iter=100)
model.fit(X, y)
if (model.n_iter_ >= 100).any():
    raise RuntimeError("logistic regression did not converge")
"""

WAIVED = """
from sklearn.linear_model import LogisticRegression
# ANALYSIS_OK[model-fit]: convergence is checked in build/model_fit_summary.tsv by the downstream report
model = LogisticRegression(max_iter=100)
model.fit(X, y)
"""


def test_unchecked_model_fit_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_unchecked_model_fit_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unchecked_model_fit_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
