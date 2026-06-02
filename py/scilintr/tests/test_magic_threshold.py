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


# ---------------------------------------------------------------------------
# Natural-floor exemption: `> 0` / `>= 0` filters drop empty/zero entries
# (the algebraic floor of a count/probability), not a tunable scientific cutoff.
# See issue #4.
# ---------------------------------------------------------------------------

FLOOR_GT_ZERO = """
import pandas as pd
deg = pd.read_csv("deg.csv")["degree"]
deg_pos = deg[deg > 0]
"""

FLOOR_GE_ZERO = """
import pandas as pd
p = pd.read_csv("p.csv")["prob"]
p = p[p >= 0]
"""

CUTOFF_NOT_ZERO = """
import pandas as pd
df = pd.read_csv("de.tsv")
sig = df[df["padj"] > 0.05]
"""

NONZERO_FLOOR_STILL_FLAGGED = """
import pandas as pd
df = pd.read_csv("de.tsv")
hi = df[df["logFC"] > 1]
"""

LT_ZERO_STILL_FLAGGED = """
import pandas as pd
df = pd.read_csv("de.tsv")
neg = df[df["x"] < 0]
"""

MIXED_FLOOR_AND_CUTOFF = """
import pandas as pd
df = pd.read_csv("de.tsv")
sub = df[(df["degree"] > 0) & (df["padj"] < 0.05)]
"""


def test_magic_threshold_exempts_gt_zero_floor(has_finding):
    assert not has_finding(FLOOR_GT_ZERO, RULE)


def test_magic_threshold_exempts_ge_zero_floor(has_finding):
    assert not has_finding(FLOOR_GE_ZERO, RULE)


def test_magic_threshold_still_flags_nonzero_gt_cutoff(has_finding):
    # `> 0.05` is a genuine cutoff, not a floor — must stay flagged.
    assert has_finding(CUTOFF_NOT_ZERO, RULE)


def test_magic_threshold_still_flags_gt_one(has_finding):
    # Only literal 0 is a floor; `> 1` is a real logFC cutoff.
    assert has_finding(NONZERO_FLOOR_STILL_FLAGGED, RULE)


def test_magic_threshold_still_flags_lt_zero(has_finding):
    # The floor exemption is scoped to `>` / `>=`; `< 0` is a sign filter we keep flagging.
    assert has_finding(LT_ZERO_STILL_FLAGGED, RULE)


def test_magic_threshold_flags_cutoff_but_not_floor_in_mixed_filter(findings_for):
    # `> 0` floor exempt, `< 0.05` cutoff still flagged → exactly one finding.
    findings = findings_for(MIXED_FLOOR_AND_CUTOFF, RULE)
    assert len(findings) == 1, (
        f"expected only the 0.05 cutoff to be flagged, got {len(findings)}: {findings}"
    )
