"""Rule: unchecked-merge — pandas merge without validate= cardinality check.

Inner merges silently drop rows when keys don't match on both sides, so the
combined frame can be smaller than the caller expected. ``validate=`` makes the
expected cardinality explicit and turns mismatches into a loud error instead of
a quiet truncation.
"""

from __future__ import annotations

RULE = "unchecked-merge"

BAD = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
batch_info = pd.read_csv("batches.tsv")
merged = metadata.merge(batch_info, on="sample_id")
"""

BAD_INNER_DROP = """
import pandas as pd
left = pd.read_csv("left.tsv")
right = pd.read_csv("right.tsv")
combined = left.merge(right, on="record_id", how="inner")
"""

GOOD = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
batch_info = pd.read_csv("batches.tsv")
merged = metadata.merge(batch_info, on="sample_id", how="left", validate="one_to_one")
"""

WAIVED = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
batch_info = pd.read_csv("batches.tsv")
# ANALYSIS_OK[join]: sample sets verified identical upstream by build/checks.py
merged = metadata.merge(batch_info, on="sample_id")
"""


def test_unchecked_merge_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_unchecked_merge_flags_inner_drop(has_finding):
    assert has_finding(BAD_INNER_DROP, RULE)


def test_unchecked_merge_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unchecked_merge_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


BAD_NAME_FORM = """
from pandas import merge
import pandas as pd
metadata = pd.read_csv("meta.tsv")
batch_info = pd.read_csv("batches.tsv")
combined = merge(metadata, batch_info, on="sample_id")
"""


def test_unchecked_merge_flags_name_form(has_finding):
    # `from pandas import merge; merge(...)` is a Call(func=Name), not a method call.
    assert has_finding(BAD_NAME_FORM, RULE)
