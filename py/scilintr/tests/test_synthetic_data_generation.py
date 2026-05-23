"""Rule: synthetic-data-generation — random distribution assigned to a data-like variable."""

from __future__ import annotations

RULE = "synthetic-data-generation"

BAD = """
import numpy as np
counts = np.random.poisson(10, size=(20000, 48))
"""

BAD_NORMAL = """
import numpy as np
expr = np.random.normal(0, 1, size=(20000, 48))
"""

BAD_FALLBACK = """
import numpy as np
from pathlib import Path

counts_path = Path("data/counts.tsv")
if not counts_path.exists():
    counts = np.random.normal(size=(1000, 12))
else:
    counts = read_counts(counts_path)
"""

GOOD = """
import numpy as np
SEED = 42
rng = np.random.default_rng(SEED)
permutation = rng.permutation(48)
"""

WAIVED = """
import numpy as np
# ANALYSIS_OK[simulation-only]: synthetic counts for the null-model permutation test
counts = np.random.poisson(10, size=(20000, 48))
"""


def test_synthetic_data_generation_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_synthetic_data_generation_flags_normal(has_finding):
    assert has_finding(BAD_NORMAL, RULE)


def test_synthetic_data_generation_flags_fallback(has_finding):
    assert has_finding(BAD_FALLBACK, RULE)


def test_synthetic_data_generation_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_synthetic_data_generation_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
