"""Rule: silent-stub-fallback.

A third silent-fallback costume (issue #7), sibling to ``silent-pass`` and
``return-none-on-missing-input``: an ``except`` handler that defines a no-op /
``None``-returning *stub function* (or rebinds a name to a no-op lambda) so the
failure path silently degrades behavior instead of raising.

Same three-test shape as every rule: flags-bad, passes-good, respects-waiver.
The extra cases pin down the boundary that makes this rule safe — a *real*
fallback implementation (one that does work) must NOT be flagged.
"""

from __future__ import annotations

# -------------------- flagged: no-op stub costumes --------------------

# The real-world repro from the issue: optional dependency degrades to a no-op.
BAD_DEF_STUB = """
try:
    from register_value import register_value
except ModuleNotFoundError:
    def register_value(*_args, **_kwargs):
        return None
"""

# `def f(...): pass` is the same costume as `return None`.
BAD_DEF_STUB_PASS = """
try:
    from plugin import emit
except ImportError:
    def emit(*_args, **_kwargs):
        pass
"""

# `def f(...): ...` (Ellipsis body) — likewise a no-op.
BAD_DEF_STUB_ELLIPSIS = """
try:
    from plugin import emit
except ImportError:
    def emit(*_args, **_kwargs):
        ...
"""

# Rebinding a name to a no-op lambda is the lambda spelling of the same stub.
BAD_LAMBDA_REBIND = """
try:
    from register_value import register_value
except ModuleNotFoundError:
    register_value = lambda *_args, **_kwargs: None
"""

# `lambda *a, **k: ...` is the Ellipsis spelling of the same no-op lambda.
BAD_LAMBDA_REBIND_ELLIPSIS = """
try:
    from plugin import emit
except ImportError:
    emit = lambda *_args, **_kwargs: ...
"""


def test_silent_stub_fallback_flags_def_stub(has_finding):
    assert has_finding(BAD_DEF_STUB, "silent-stub-fallback")


def test_silent_stub_fallback_flags_def_stub_pass(has_finding):
    assert has_finding(BAD_DEF_STUB_PASS, "silent-stub-fallback")


def test_silent_stub_fallback_flags_def_stub_ellipsis(has_finding):
    assert has_finding(BAD_DEF_STUB_ELLIPSIS, "silent-stub-fallback")


def test_silent_stub_fallback_flags_lambda_rebind(has_finding):
    assert has_finding(BAD_LAMBDA_REBIND, "silent-stub-fallback")


def test_silent_stub_fallback_flags_lambda_rebind_ellipsis(has_finding):
    assert has_finding(BAD_LAMBDA_REBIND_ELLIPSIS, "silent-stub-fallback")


# -------------------- not flagged: real fallbacks / unrelated defs --------------------

# A fallback that actually does the work is the correct fix, not a no-op stub.
GOOD_REAL_FALLBACK = """
_STORE = {}

try:
    from fast_register import register_value
except ModuleNotFoundError:
    def register_value(key, value):
        _STORE[key] = value
"""

# Re-raising is the other correct shape — and there is no stub at all.
GOOD_RERAISE = """
try:
    from register_value import register_value
except ModuleNotFoundError:
    raise
"""

# A no-op function defined in ordinary code (not on a failure path) is not this
# pattern — the rule must be scoped to except handlers.
GOOD_NOOP_NOT_IN_EXCEPT = """
def register_value(*_args, **_kwargs):
    return None
"""


def test_silent_stub_fallback_passes_real_fallback(has_finding):
    assert not has_finding(GOOD_REAL_FALLBACK, "silent-stub-fallback")


def test_silent_stub_fallback_passes_reraise(has_finding):
    assert not has_finding(GOOD_RERAISE, "silent-stub-fallback")


def test_silent_stub_fallback_passes_noop_outside_except(has_finding):
    assert not has_finding(GOOD_NOOP_NOT_IN_EXCEPT, "silent-stub-fallback")


# -------------------- waiver --------------------

WAIVED_DEF_STUB = """
try:
    from register_value import register_value
except ModuleNotFoundError:
    # ANALYSIS_OK[optional-dependency]: plugin truly optional; downstream re-reads numbers.json
    def register_value(*_args, **_kwargs):
        return None
"""


def test_silent_stub_fallback_respects_waiver(has_finding):
    assert not has_finding(WAIVED_DEF_STUB, "silent-stub-fallback")
