"""Rule: unannotated-transform — combat / regress_out / residualize without justification."""

from __future__ import annotations

RULE = "unannotated-transform"

BAD_COMBAT = """
expr_corrected = combat(expr, batch=metadata["batch"])
"""

BAD_REGRESS_OUT = """
import scanpy as sc
sc.pp.regress_out(adata, ["pct_counts_mt"])
"""

GOOD = """
import pandas as pd
expr = pd.read_csv("expr.tsv", index_col=0)
"""

WAIVED = """
# ANALYSIS_OK[batch-correction]: sequencing batch only; treatment is not included as a covariate
expr_corrected = combat(expr, batch=metadata["batch"])
"""


def test_unannotated_transform_flags_combat(has_finding):
    assert has_finding(BAD_COMBAT, RULE)


def test_unannotated_transform_flags_regress_out(has_finding):
    assert has_finding(BAD_REGRESS_OUT, RULE)


def test_unannotated_transform_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unannotated_transform_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
