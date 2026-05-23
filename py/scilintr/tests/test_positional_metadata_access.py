"""Rule: positional-metadata-access — anonymous .iloc[:, N] on metadata-like frames."""

from __future__ import annotations

RULE = "positional-metadata-access"

BAD = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
condition = metadata.iloc[:, 3]
"""

GOOD = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
TREATMENT_COL = "treatment"
condition = metadata[TREATMENT_COL]
"""

WAIVED = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
assert metadata.columns[3] == "treatment"
# ANALYSIS_OK[positional-access]: column index 3 verified by the assertion above
condition = metadata.iloc[:, 3]
"""


def test_positional_metadata_access_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_positional_metadata_access_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_positional_metadata_access_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


ROW_ONLY = """
import pandas as pd
audit = pd.read_csv("audit.tsv")
first_alt = audit[audit["predicted_type"] == "AltType"].iloc[0]
"""

ROW_RANGE = """
import pandas as pd
df = pd.read_csv("data.tsv")
head = df.iloc[0:10]
"""


def test_positional_metadata_access_ignores_row_only_iloc(has_finding):
    # `df.iloc[0]` is row selection, not anonymous column access.
    assert not has_finding(ROW_ONLY, RULE)


def test_positional_metadata_access_ignores_row_range(has_finding):
    assert not has_finding(ROW_RANGE, RULE)
