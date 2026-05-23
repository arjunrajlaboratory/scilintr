"""Rule: unannotated-missingness — fillna / nan_to_num / errors='coerce' without justification."""

from __future__ import annotations

RULE = "unannotated-missingness"

BAD_FILLNA = """
import pandas as pd
df = pd.read_csv("data.tsv")
df = df.fillna(0)
"""

BAD_COERCE = """
import pandas as pd
df = pd.read_csv("data.tsv")
df["age"] = pd.to_numeric(df["age"], errors="coerce")
"""

GOOD = """
import pandas as pd
df = pd.read_csv("data.tsv")
# leave NaNs as-is; downstream models handle missingness explicitly
print(df.shape)
"""

WAIVED = """
import pandas as pd
df = pd.read_csv("data.tsv")
# ANALYSIS_OK[imputation]: missing library_prep filled with 'unknown' for plotting only;
# not used by the DE model
df["library_prep"] = df["library_prep"].fillna("unknown")
"""


def test_unannotated_missingness_flags_fillna(has_finding):
    assert has_finding(BAD_FILLNA, RULE)


def test_unannotated_missingness_flags_coerce(has_finding):
    assert has_finding(BAD_COERCE, RULE)


def test_unannotated_missingness_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unannotated_missingness_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
