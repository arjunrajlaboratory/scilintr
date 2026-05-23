"""Rule: runtime-assert — ``assert`` used outside ``tests/`` for runtime correctness checks.

``assert`` statements are stripped when Python runs with ``-O``, so anything
load-bearing must raise explicitly.
"""

from __future__ import annotations

RULE = "runtime-assert"

BAD = """
def compute_f1(preds, gt):
    assert len(preds) == len(gt)
    return sum(p == g for p, g in zip(preds, gt)) / len(preds)
"""

GOOD = """
def compute_f1(preds, gt):
    if len(preds) != len(gt):
        raise ValueError(f"length mismatch: {len(preds)} vs {len(gt)}")
    return sum(p == g for p, g in zip(preds, gt)) / len(preds)
"""

WAIVED = """
def compute_f1(preds, gt):
    # ANALYSIS_OK[runtime-assert]: invariant guaranteed by callers' static typing;
    # this is a developer tripwire only, not a runtime check
    assert len(preds) == len(gt)
    return sum(p == g for p, g in zip(preds, gt)) / len(preds)
"""

LITERAL_ASSERT_NOT_FLAGGED = """
def todo_stub():
    assert False, "TODO: implement"
"""


def test_runtime_assert_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE, filename="src/scoring.py")


def test_runtime_assert_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE, filename="src/scoring.py")


def test_runtime_assert_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE, filename="src/scoring.py")


def test_runtime_assert_ignores_test_files(has_finding):
    # Same bad pattern, but in a test file — asserts are first-class there.
    assert not has_finding(BAD, RULE, filename="tests/test_scoring.py")


def test_runtime_assert_ignores_literal_tripwire(has_finding):
    # `assert False, "TODO"` is obvious developer intent, not a runtime check.
    assert not has_finding(LITERAL_ASSERT_NOT_FLAGGED, RULE, filename="src/scoring.py")


def test_runtime_assert_ignores_integration_tests_dir(has_finding):
    assert not has_finding(BAD, RULE, filename="integration_tests/check.py")


def test_runtime_assert_ignores_e2e_tests_dir(has_finding):
    assert not has_finding(BAD, RULE, filename="src/e2e_tests/path_validation.py")
