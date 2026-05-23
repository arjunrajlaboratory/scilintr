"""Rule: magic-threshold — bare numeric literals in DataFrame boolean filters."""

from __future__ import annotations

RULE = "magic-threshold"

BAD = """
import pandas as pd
results = pd.read_csv("de.tsv")
sig = results[results["padj"] < 0.05]
"""

GOOD = """
import pandas as pd
FDR_THRESHOLD = 0.05
results = pd.read_csv("de.tsv")
sig = results[results["padj"] < FDR_THRESHOLD]
"""

WAIVED = """
import pandas as pd
results = pd.read_csv("de.tsv")
# ANALYSIS_OK[threshold]: 0.05 is the standard FDR cutoff per project decision
sig = results[results["padj"] < 0.05]
"""


def test_magic_threshold_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_magic_threshold_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_magic_threshold_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


BAD_NESTED_BOOLOP = """
import pandas as pd
df = pd.read_csv("de.tsv")
sig = df[(df["padj"] < 0.05) | ((df["logFC"] > 1) & (df["pval"] < 0.01))]
"""


def test_magic_threshold_recurses_into_nested_boolop(findings_for):
    # All three numeric thresholds (0.05, 1, 0.01) should be flagged.
    findings = findings_for(BAD_NESTED_BOOLOP, RULE)
    assert len(findings) >= 3, (
        f"expected >=3 findings for nested BoolOp; got {len(findings)}"
    )
