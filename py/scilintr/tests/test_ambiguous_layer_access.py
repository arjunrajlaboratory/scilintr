"""Rule: ambiguous-layer-access — adata.X / adata.raw.X without an explicit layer label."""

from __future__ import annotations

RULE = "ambiguous-layer-access"

BAD_X = """
import anndata as ad
adata = ad.read_h5ad("data.h5ad")
x = adata.X
"""

BAD_RAW = """
import anndata as ad
adata = ad.read_h5ad("data.h5ad")
x = adata.raw.X
"""

GOOD = """
import anndata as ad
adata = ad.read_h5ad("data.h5ad")
EXPRESSION_LAYER = "lognorm"
x = adata.layers[EXPRESSION_LAYER]
"""

WAIVED = """
import anndata as ad
adata = ad.read_h5ad("data.h5ad")
# ANALYSIS_OK[layer-choice]: adata.X is set by upstream preprocessing to lognorm CPM (see specification.md)
x = adata.X
"""


def test_ambiguous_layer_access_flags_X(has_finding):
    assert has_finding(BAD_X, RULE)


def test_ambiguous_layer_access_flags_raw_X(has_finding):
    assert has_finding(BAD_RAW, RULE)


def test_ambiguous_layer_access_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_ambiguous_layer_access_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
