"""Rule: unchecked-cache — return cached output without comparing input fingerprints."""

from __future__ import annotations

RULE = "unchecked-cache"

BAD = """
import pandas as pd
from pathlib import Path

def get_result(output: Path):
    if output.exists():
        return pd.read_csv(output)
    return compute(output)
"""

GOOD = """
import pandas as pd
from pathlib import Path

def get_result(output: Path, inputs: list[Path]):
    if cache_is_valid(output, inputs):
        return pd.read_csv(output)
    return compute(output, inputs)
"""

WAIVED = """
import pandas as pd
from pathlib import Path

def get_result(output: Path):
    # ANALYSIS_OK[cache]: output is invalidated by snakemake rule when any input changes
    if output.exists():
        return pd.read_csv(output)
    return compute(output)
"""


def test_unchecked_cache_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_unchecked_cache_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unchecked_cache_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


THREAD_FALSE_POSITIVE = """
from pathlib import Path

def f(p: Path):
    if p.exists():
        return p.thread()
    raise FileNotFoundError(p)
"""


SPREAD_FALSE_POSITIVE = """
from pathlib import Path

def f(p: Path):
    if p.exists():
        return analysis.spread(p)
    raise FileNotFoundError(p)
"""


NON_NAME_EXISTS_CHECK = """
def f(registry):
    if registry["output"].exists():
        return some_unrelated_value
    return None
"""


def test_unchecked_cache_ignores_thread(has_finding):
    # "thread" matches `"read" in attr.lower()` but is not a data reader.
    assert not has_finding(THREAD_FALSE_POSITIVE, RULE)


def test_unchecked_cache_ignores_spread(has_finding):
    assert not has_finding(SPREAD_FALSE_POSITIVE, RULE)


def test_unchecked_cache_ignores_non_name_exists_check(has_finding):
    # When the `.exists()` receiver isn't a plain Name, we can't reliably tie the
    # return to the cached path, so we shouldn't fire.
    assert not has_finding(NON_NAME_EXISTS_CHECK, RULE)
