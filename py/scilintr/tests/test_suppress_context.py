"""Rule: suppress-context (issue #8).

``contextlib.suppress(...)`` is the context-manager spelling of
``try/except: pass`` — it swallows the listed exceptions with no handler block,
so none of the ``ExceptHandler``-based silent-fallback rules can see it.

Like ``silent-pass``, every exception type is flagged (high recall); an
``ANALYSIS_OK[...]`` waiver above the ``with``, trailing it, or as the first
line of the block suppresses.
"""

from __future__ import annotations

RULE = "suppress-context"

# -------------------- flagged --------------------

BAD_FROM_IMPORT = """
from contextlib import suppress

with suppress(Exception):
    register_value(key, val)
"""

BAD_MODULE_ATTR = """
import contextlib

with contextlib.suppress(KeyError):
    del cache[key]
"""

BAD_MODULE_ALIAS = """
import contextlib as cl

with cl.suppress(OSError):
    os.remove(tmp)
"""

BAD_NAME_ALIAS = """
from contextlib import suppress as ignoring

with ignoring(ValueError):
    x = int(s)
"""

BAD_MULTI_ITEM = """
from contextlib import suppress

with open(path) as fh, suppress(UnicodeDecodeError):
    text = fh.read()
"""

BAD_ASYNC = """
from contextlib import suppress

async def go():
    async with suppress(Exception):
        await fetch()
"""

BAD_MULTI_EXC = """
from contextlib import suppress

with suppress(KeyError, IndexError):
    v = table[k][0]
"""

# -------------------- not flagged --------------------

GOOD_TRY_RAISE = """
try:
    register_value(key, val)
except KeyError:
    log.exception("register failed")
    raise
"""

GOOD_OTHER_CONTEXT = """
import numpy as np

with np.errstate(divide="ignore"):
    r = a / b
with open(path) as fh:
    text = fh.read()
"""

GOOD_UNRELATED_SUPPRESS_METHOD = """
with self.notifier.suppress():
    update()
"""

GOOD_USER_DEFINED_SUPPRESS = """
from mylib import suppress

with suppress():
    notify()
"""

GOOD_LOCAL_SUPPRESS_DEF = """
from contextlib import contextmanager

@contextmanager
def suppress():
    yield

with suppress():
    notify()
"""

# -------------------- waivers --------------------

WAIVED_ABOVE = """
from contextlib import suppress

# ANALYSIS_OK[best-effort]: temp-file cleanup; a leftover file is harmless
with suppress(FileNotFoundError):
    os.remove(tmp)
"""

WAIVED_TRAILING = """
from contextlib import suppress

with suppress(FileNotFoundError):  # ANALYSIS_OK[best-effort]: cleanup only
    os.remove(tmp)
"""

WAIVED_INSIDE = """
from contextlib import suppress

with suppress(FileNotFoundError):
    # ANALYSIS_OK[best-effort]: cleanup only
    os.remove(tmp)
"""

WAIVED_ABOVE_MULTILINE_HEADER = """
from contextlib import suppress

# ANALYSIS_OK[best-effort]: cleanup only
with (
    open(a) as f,
    open(b) as g,
    suppress(OSError),
):
    body()
"""


def test_suppress_context_flags_from_import(has_finding):
    assert has_finding(BAD_FROM_IMPORT, RULE)


def test_suppress_context_flags_module_attr(has_finding):
    assert has_finding(BAD_MODULE_ATTR, RULE)


def test_suppress_context_flags_module_alias(has_finding):
    assert has_finding(BAD_MODULE_ALIAS, RULE)


def test_suppress_context_flags_name_alias(has_finding):
    assert has_finding(BAD_NAME_ALIAS, RULE)


def test_suppress_context_flags_any_item_of_multi_item_with(has_finding):
    assert has_finding(BAD_MULTI_ITEM, RULE)


def test_suppress_context_flags_async_with(has_finding):
    assert has_finding(BAD_ASYNC, RULE)


def test_suppress_context_flags_multiple_exception_types(has_finding):
    assert has_finding(BAD_MULTI_EXC, RULE)


def test_suppress_context_one_finding_per_with(findings_for):
    assert len(findings_for(BAD_FROM_IMPORT, RULE)) == 1


def test_suppress_context_passes_try_with_raise(has_finding):
    assert not has_finding(GOOD_TRY_RAISE, RULE)


def test_suppress_context_passes_other_context_managers(has_finding):
    assert not has_finding(GOOD_OTHER_CONTEXT, RULE)


def test_suppress_context_passes_unrelated_suppress_method(has_finding):
    assert not has_finding(GOOD_UNRELATED_SUPPRESS_METHOD, RULE)


def test_suppress_context_passes_non_contextlib_suppress(has_finding):
    assert not has_finding(GOOD_USER_DEFINED_SUPPRESS, RULE)
    assert not has_finding(GOOD_LOCAL_SUPPRESS_DEF, RULE)


def test_suppress_context_respects_waiver_above_multiline_header(has_finding):
    assert not has_finding(WAIVED_ABOVE_MULTILINE_HEADER, RULE)


def test_suppress_context_respects_waiver_above(has_finding):
    assert not has_finding(WAIVED_ABOVE, RULE)


def test_suppress_context_respects_trailing_waiver(has_finding):
    assert not has_finding(WAIVED_TRAILING, RULE)


def test_suppress_context_respects_waiver_inside_block(has_finding):
    assert not has_finding(WAIVED_INSIDE, RULE)


def test_suppress_context_flagged_under_no_waivers(lint):
    findings = lint(WAIVED_ABOVE, respect_waivers=False)
    assert any(f.rule == RULE for f in findings)
