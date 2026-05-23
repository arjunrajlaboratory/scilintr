"""Rule: unannotated-filter — silent .dropna() or sentinel-then-filter on data frames.

Two shapes covered:

* ``.dropna()`` with no justification of what's being removed and why.
* Sentinel-then-filter: assign ``""`` (or another sentinel) to "unknown" rows
  upstream, then subscript-filter those rows out downstream. The headline
  metric ends up computed only over the surviving subset and reported as if
  it covered the full input.
"""

from __future__ import annotations

RULE = "unannotated-filter"

BAD_DROPNA = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
metadata = metadata.dropna()
"""

BAD_SENTINEL_FILTER = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
metadata["label"] = metadata["label"].fillna("")
keep = metadata[metadata["label"] != ""]
"""

GOOD = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
# use metadata as-is; missing rows are an upstream contract violation
print(metadata.head())
"""

WAIVED = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
# ANALYSIS_OK[sample-filter]: drop samples failing predeclared QC; ledger in build/dropped.tsv
metadata = metadata.dropna()
"""


def test_unannotated_filter_flags_dropna(has_finding):
    assert has_finding(BAD_DROPNA, RULE)


def test_unannotated_filter_flags_sentinel_filter(has_finding):
    assert has_finding(BAD_SENTINEL_FILTER, RULE)


def test_unannotated_filter_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unannotated_filter_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


IS_NOT_NONE_FILTER = """
import pandas as pd
df = pd.read_csv("data.tsv")
clean = df[df["sample_id"].notnull()]
clean2 = df[df["sample_id"] is not None]
"""


def test_unannotated_filter_does_not_flag_is_not_none(has_finding):
    # `is not None` is the standard idiom for non-null filtering, not a hidden sentinel.
    assert not has_finding(IS_NOT_NONE_FILTER, RULE)
