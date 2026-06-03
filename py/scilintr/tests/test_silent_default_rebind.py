"""Rule: silent-default-rebind.

Fifth silent-fallback costume: the ``except`` body rebinds a name to a default /
empty value (``{}`` / ``[]`` / ``None`` / ``0`` / ``NaN``) so the analysis
proceeds on a placeholder instead of raising. This is the *value*-rebind
counterpart to ``silent-stub-fallback`` (which rebinds to a no-op *callable*)
and the assignment counterpart to ``silent-fallback-return``.

The boundary: rebinding to a *real* recovered value (an alternate loader, a
computed default) is legitimate and must NOT be flagged.
"""

from __future__ import annotations

# -------------------- flagged: default-value rebinds --------------------

BAD_REBIND_EMPTY_DICT = """
def get_config(path):
    try:
        config = load_config(path)
    except FileNotFoundError:
        config = {}
    return config
"""

BAD_REBIND_EMPTY_LIST = """
def get_rows(path):
    try:
        rows = read_rows(path)
    except KeyError:
        rows = []
    return rows
"""

BAD_REBIND_NONE = """
def get_model(path):
    try:
        model = load_model(path)
    except OSError:
        model = None
    return model
"""

BAD_REBIND_NAN = """
import numpy as np

def get_score(row):
    try:
        score = compute(row)
    except RuntimeError:
        score = np.nan
    return score
"""


def test_silent_default_rebind_flags_empty_dict(has_finding):
    assert has_finding(BAD_REBIND_EMPTY_DICT, "silent-default-rebind")


def test_silent_default_rebind_flags_empty_list(has_finding):
    assert has_finding(BAD_REBIND_EMPTY_LIST, "silent-default-rebind")


def test_silent_default_rebind_flags_none(has_finding):
    assert has_finding(BAD_REBIND_NONE, "silent-default-rebind")


def test_silent_default_rebind_flags_nan(has_finding):
    assert has_finding(BAD_REBIND_NAN, "silent-default-rebind")


# -------------------- not flagged: real recovery / unrelated assigns --------------------

# Rebinding to a genuine alternate value is legitimate recovery, not a degrade.
GOOD_REAL_RECOVERY = """
def get_config(path, backup):
    try:
        config = load_config(path)
    except FileNotFoundError:
        config = load_config(backup)
    return config
"""

GOOD_RERAISE = """
def get_config(path):
    try:
        config = load_config(path)
    except FileNotFoundError:
        raise
    return config
"""

# A default assignment in ordinary code (not on a failure path) is not this pattern.
GOOD_DEFAULT_NOT_IN_EXCEPT = """
def build(options):
    config = {}
    config.update(options)
    return config
"""

# Rebinding to a no-op lambda is silent-stub-fallback's job, not this rule's.
GOOD_LAMBDA_IS_STUB_RULE = """
try:
    from plugin import emit
except ImportError:
    emit = lambda *a, **k: None
"""


def test_silent_default_rebind_passes_real_recovery(has_finding):
    assert not has_finding(GOOD_REAL_RECOVERY, "silent-default-rebind")


def test_silent_default_rebind_passes_reraise(has_finding):
    assert not has_finding(GOOD_RERAISE, "silent-default-rebind")


def test_silent_default_rebind_passes_default_outside_except(has_finding):
    assert not has_finding(GOOD_DEFAULT_NOT_IN_EXCEPT, "silent-default-rebind")


def test_silent_default_rebind_passes_lambda_rebind(has_finding):
    # The lambda rebind belongs to silent-stub-fallback; this rule must not also claim it.
    assert not has_finding(GOOD_LAMBDA_IS_STUB_RULE, "silent-default-rebind")


# -------------------- waiver --------------------

WAIVED_REBIND = """
def get_config(path):
    try:
        config = load_config(path)
    except FileNotFoundError:
        # ANALYSIS_OK[optional-input]: missing config means defaults-only run; documented in methods
        config = {}
    return config
"""


def test_silent_default_rebind_respects_waiver(has_finding):
    assert not has_finding(WAIVED_REBIND, "silent-default-rebind")
