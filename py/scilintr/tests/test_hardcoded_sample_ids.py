"""Rule: hardcoded-sample-ids — list of sample-ID strings in code instead of a ledger."""

from __future__ import annotations

RULE = "hardcoded-sample-ids"

BAD = """
import pandas as pd
exclude = ["S17", "S23"]
metadata = pd.read_csv("meta.tsv")
metadata = metadata[~metadata["sample_id"].isin(exclude)]
"""

BAD_DROP_NAMED = """
import pandas as pd
dropped_samples = ["S04", "S11", "S29"]
metadata = pd.read_csv("meta.tsv")
metadata = metadata[~metadata["sample_id"].isin(dropped_samples)]
"""

GOOD = """
import pandas as pd
exclude = pd.read_csv("build/dropped_samples.tsv")["sample_id"].tolist()
metadata = pd.read_csv("meta.tsv")
metadata = metadata[~metadata["sample_id"].isin(exclude)]
"""

WAIVED = """
import pandas as pd
# ANALYSIS_OK[sample-exclusion]: S17, S23 failed predeclared sequencing QC; see build/dropped_samples.tsv
exclude = ["S17", "S23"]
metadata = pd.read_csv("meta.tsv")
metadata = metadata[~metadata["sample_id"].isin(exclude)]
"""


def test_hardcoded_sample_ids_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_hardcoded_sample_ids_flags_named_drop_list(has_finding):
    assert has_finding(BAD_DROP_NAMED, RULE)


def test_hardcoded_sample_ids_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_hardcoded_sample_ids_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
