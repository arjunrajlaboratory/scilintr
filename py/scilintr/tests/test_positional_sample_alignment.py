"""Rule: positional-sample-alignment — assigning columns/index across frames by order."""

from __future__ import annotations

RULE = "positional-sample-alignment"

BAD = """
import pandas as pd
counts = pd.read_csv("counts.tsv", index_col=0)
metadata = pd.read_csv("meta.tsv")
counts.columns = metadata["sample_id"]
"""

GOOD = """
import pandas as pd
counts = pd.read_csv("counts.tsv", index_col=0)
metadata = pd.read_csv("meta.tsv")
counts = counts.loc[:, metadata["sample_id"]]
assert list(counts.columns) == list(metadata["sample_id"])
"""

WAIVED = """
import pandas as pd
counts = pd.read_csv("counts.tsv", index_col=0)
metadata = pd.read_csv("meta.tsv")
# ANALYSIS_OK[id-alignment]: order guaranteed by upstream pipeline contract; reordered downstream
counts.columns = metadata["sample_id"]
"""


def test_positional_sample_alignment_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_positional_sample_alignment_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_positional_sample_alignment_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


CONFIG_DICT_FALSE_POSITIVE = """
import pandas as pd
df = pd.read_csv("data.tsv")
config = {"new_columns": ["a", "b", "c"]}
df.columns = config["new_columns"]
"""

SELF_ATTR_FALSE_POSITIVE = """
class Loader:
    def assign(self, df):
        df.columns = self.column_names
"""


def test_positional_sample_alignment_ignores_config_dict(has_finding):
    # `config["new_columns"]` is a list of names, not a cross-frame column reference.
    assert not has_finding(CONFIG_DICT_FALSE_POSITIVE, RULE)


def test_positional_sample_alignment_ignores_self_attr(has_finding):
    # `self.column_names` may well be a list literal — not a Series from another frame.
    assert not has_finding(SELF_ATTR_FALSE_POSITIVE, RULE)
