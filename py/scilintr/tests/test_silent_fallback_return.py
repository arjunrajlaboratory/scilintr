"""Rule: silent-fallback-return.

Fourth silent-fallback costume: the ``except`` body itself ``return``s a degraded
default (``None`` / ``[]`` / ``{}`` / ``0`` / ``NaN``) instead of raising. Sibling
to ``silent-pass`` (which only matches ``pass``/``continue``) and
``silent-stub-fallback`` (which matches a stub *def*, not a ``return``).

The boundary that keeps this safe: returning a *real* recovery value (a cache,
an alternate computation) must NOT be flagged — only degraded placeholders are.
"""

from __future__ import annotations

# -------------------- flagged: degraded-default returns --------------------

BAD_RETURN_NONE = """
def parse(x):
    try:
        return int(x)
    except ValueError:
        return None
"""

BAD_RETURN_EMPTY_LIST = """
def records(path):
    try:
        return read_rows(path)
    except KeyError:
        return []
"""

BAD_RETURN_NAN = """
import numpy as np

def score(row):
    try:
        return compute(row)
    except RuntimeError:
        return np.nan
"""

BAD_BARE_RETURN = """
def emit(payload):
    try:
        send(payload)
    except ConnectionError:
        return
"""


def test_silent_fallback_return_flags_return_none(has_finding):
    assert has_finding(BAD_RETURN_NONE, "silent-fallback-return")


def test_silent_fallback_return_flags_empty_list(has_finding):
    assert has_finding(BAD_RETURN_EMPTY_LIST, "silent-fallback-return")


def test_silent_fallback_return_flags_nan(has_finding):
    assert has_finding(BAD_RETURN_NAN, "silent-fallback-return")


def test_silent_fallback_return_flags_bare_return(has_finding):
    assert has_finding(BAD_BARE_RETURN, "silent-fallback-return")


# -------------------- not flagged: real recovery / unrelated returns --------------------

# Returning a genuine recovery value (a cache) is legitimate, not a degrade.
GOOD_REAL_RECOVERY = """
def fetch(key, cache):
    try:
        return remote_get(key)
    except TimeoutError:
        return cache[key]
"""

GOOD_RERAISE = """
def parse(x):
    try:
        return int(x)
    except ValueError:
        raise
"""

# `return None` in ordinary control flow (not on a failure path) is not this pattern.
GOOD_RETURN_NONE_NOT_IN_EXCEPT = """
def lookup(table, key):
    if key not in table:
        return None
    return table[key]
"""


def test_silent_fallback_return_passes_real_recovery(has_finding):
    assert not has_finding(GOOD_REAL_RECOVERY, "silent-fallback-return")


def test_silent_fallback_return_passes_reraise(has_finding):
    assert not has_finding(GOOD_RERAISE, "silent-fallback-return")


def test_silent_fallback_return_passes_return_none_outside_except(has_finding):
    assert not has_finding(GOOD_RETURN_NONE_NOT_IN_EXCEPT, "silent-fallback-return")


# -------------------- waiver --------------------

WAIVED_RETURN_NONE = """
def parse(x):
    try:
        return int(x)
    except ValueError:
        # ANALYSIS_OK[degraded-fallback]: malformed rows are dropped by design; count logged upstream
        return None
"""


def test_silent_fallback_return_respects_waiver(has_finding):
    assert not has_finding(WAIVED_RETURN_NONE, "silent-fallback-return")
