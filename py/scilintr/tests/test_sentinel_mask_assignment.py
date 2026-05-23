"""Rule: sentinel-mask-assignment — assigning a boolean mask from a sentinel comparison.

The pattern: upstream code assigns ``""`` to rows it can't resolve (treating the
empty string as a "missing" marker); a later assignment like
``labeled = label_arr != ""`` produces a mask that quietly partitions the dataset
into "kept" and "dropped" without declaring intent.

Distinct from ``unannotated-filter``, which catches the same idea expressed inline
inside a subscript (``df[df["x"] != ""]``).
"""

from __future__ import annotations

RULE = "sentinel-mask-assignment"

BAD_NEQ = """
import numpy as np
label_arr = np.array(["a", "b", "", "c"])
labeled = label_arr != ""
"""

BAD_EQ = """
import numpy as np
label_arr = np.array(["a", "b", "", "c"])
is_missing = label_arr == ""
"""

BAD_ANN_ASSIGN = """
import numpy as np
label_arr = np.array(["a", "b", "", "c"])
labeled: np.ndarray = label_arr != ""
"""

GOOD_NOTNA = """
import pandas as pd
label_series = pd.Series(["a", "b", None, "c"])
labeled = label_series.notna()
"""

GOOD_NUMERIC_NONZERO = """
import numpy as np
counts = np.array([0, 1, 0, 2])
nonzero = counts != 0
"""

GOOD_IS_NOT_NONE = """
values = [1, None, 2]
present = [v is not None for v in values]
"""

WAIVED = """
import numpy as np
label_arr = np.array(["a", "b", "", "c"])
# ANALYSIS_OK[sentinel-mask]: empty string is the upstream library's missing marker;
# documented in build/labeling_contract.md
labeled = label_arr != ""
"""


def test_sentinel_mask_assignment_flags_neq(has_finding):
    assert has_finding(BAD_NEQ, RULE)


def test_sentinel_mask_assignment_flags_eq(has_finding):
    assert has_finding(BAD_EQ, RULE)


def test_sentinel_mask_assignment_flags_ann_assign(has_finding):
    assert has_finding(BAD_ANN_ASSIGN, RULE)


def test_sentinel_mask_assignment_passes_notna(has_finding):
    # Standard nullability check — not a sentinel.
    assert not has_finding(GOOD_NOTNA, RULE)


def test_sentinel_mask_assignment_passes_nonzero(has_finding):
    # Numeric "nonzero" is intentionally out of scope; restricted to empty-string sentinels.
    assert not has_finding(GOOD_NUMERIC_NONZERO, RULE)


def test_sentinel_mask_assignment_passes_is_not_none(has_finding):
    # `is not None` is the idiomatic null filter.
    assert not has_finding(GOOD_IS_NOT_NONE, RULE)


def test_sentinel_mask_assignment_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


# Pandas vectorized AND (`&`) is `BinOp(BitAnd)`, not `BoolOp(And)`. The mask
# wrapping a Compare against the empty string still propagates downstream.
BAD_BITAND_WRAPPED = """
import pandas as pd
df = pd.read_csv("data.tsv")
has_label = df["label"].notna() & (df["label"] != "")
"""

BAD_BITOR_WRAPPED = """
import pandas as pd
df = pd.read_csv("data.tsv")
unmapped_or_missing = df["label"].isna() | (df["label"] == "")
"""

# Scalar Python `and`/`or` (BoolOp) is *not* a mask — it's a scalar boolean expression.
GOOD_SCALAR_AND_GUARD = """
prev_name = "foo"
cur_name = "FOO"
same_name = prev_name.lower() == cur_name.lower() and prev_name != ""
"""


def test_sentinel_mask_assignment_flags_bitand_wrapped(has_finding):
    assert has_finding(BAD_BITAND_WRAPPED, RULE)


def test_sentinel_mask_assignment_flags_bitor_wrapped(has_finding):
    assert has_finding(BAD_BITOR_WRAPPED, RULE)


def test_sentinel_mask_assignment_ignores_scalar_and_guard(has_finding):
    # Scalar `and` builds a scalar boolean, not a propagating mask — out of scope.
    assert not has_finding(GOOD_SCALAR_AND_GUARD, RULE)
