"""Rules: broad-exception, silent-pass, return-none-on-missing-input.

Three closely-related shapes:

* ``except Exception:`` (or bare ``except:``) catching everything in a fallback chain.
* ``except <X>: pass`` (or ``continue``) — failures are dropped without log or recovery.
* A loader returning ``None`` on missing input; the caller propagates the ``None``
  through downstream merges and the analysis silently runs on a smaller frame.
"""

from __future__ import annotations

# -------------------- broad-exception --------------------

BAD_BROAD = """
def load(path, backup):
    try:
        return load_counts(path)
    except Exception:
        return load_counts(backup)
"""

GOOD_BROAD = """
def load(path, backup):
    try:
        return load_counts(path)
    except FileNotFoundError:
        return load_counts(backup)
"""

WAIVED_BROAD = """
def fetch(dataset_id):
    # ANALYSIS_OK[api-retry]: retry same dataset_id once on transient error; no alternate fallback
    try:
        return fetch_counts(dataset_id)
    except Exception:
        return fetch_counts(dataset_id)
"""


def test_broad_exception_flags_bad_code(has_finding):
    assert has_finding(BAD_BROAD, "broad-exception")


def test_broad_exception_passes_good_code(has_finding):
    assert not has_finding(GOOD_BROAD, "broad-exception")


def test_broad_exception_respects_waiver(has_finding):
    assert not has_finding(WAIVED_BROAD, "broad-exception")


# -------------------- silent-pass --------------------

BAD_SILENT_PASS = """
for stream in streams:
    try:
        results.append(query(stream))
    except Exception:
        continue
"""

GOOD_SILENT_PASS = """
for stream in streams:
    try:
        results.append(query(stream))
    except StreamError as e:
        logger.warning("stream %s failed: %s", stream, e)
        raise
"""

WAIVED_SILENT_PASS = """
for stream in streams:
    try:
        results.append(query(stream))
    except Exception:
        # ANALYSIS_OK[best-effort-fan-out]: partial results are acceptable here; failures logged downstream
        continue
"""


def test_silent_pass_flags_bad_code(has_finding):
    assert has_finding(BAD_SILENT_PASS, "silent-pass")


def test_silent_pass_passes_good_code(has_finding):
    assert not has_finding(GOOD_SILENT_PASS, "silent-pass")


def test_silent_pass_respects_waiver(has_finding):
    assert not has_finding(WAIVED_SILENT_PASS, "silent-pass")


# -------------------- return-none-on-missing-input --------------------

BAD_RETURN_NONE = """
from pathlib import Path

def load_phase1(path: Path):
    if not path.exists():
        return None
    return read_csv(path)
"""

GOOD_RETURN_NONE = """
from pathlib import Path

def load_phase1(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return read_csv(path)
"""

WAIVED_RETURN_NONE = """
from pathlib import Path

def load_phase1(path: Path):
    if not path.exists():
        # ANALYSIS_OK[optional-input]: sparse-sweep mode treats absent runs as 'skip'; caller handles None
        return None
    return read_csv(path)
"""


def test_return_none_on_missing_input_flags_bad_code(has_finding):
    assert has_finding(BAD_RETURN_NONE, "return-none-on-missing-input")


def test_return_none_on_missing_input_passes_good_code(has_finding):
    assert not has_finding(GOOD_RETURN_NONE, "return-none-on-missing-input")


def test_return_none_on_missing_input_respects_waiver(has_finding):
    assert not has_finding(WAIVED_RETURN_NONE, "return-none-on-missing-input")
