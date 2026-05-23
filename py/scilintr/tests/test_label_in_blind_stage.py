"""Rule: label-in-blind-stage — referencing experimental-label columns in blind QC/PCA files.

Stage is inferred from filename. Default-blind filenames contain ``blind``, ``qc``,
``pca``, ``umap``, ``tsne``, ``hvg``, ``cluster``, ``embedding``, or ``neighbors``.
"""

from __future__ import annotations

RULE = "label-in-blind-stage"

BAD = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
y = metadata["treatment"]
"""

BAD_QUERY = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
treated = metadata.query("group == 'treated'")
"""

GOOD_IN_SUPERVISED = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
y = metadata["treatment"]
"""

GOOD_NO_LABEL = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
batch = metadata["batch"]
"""

WAIVED = """
import pandas as pd
metadata = pd.read_csv("meta.tsv")
pca_coords = compute_pca(load_expr())
# ANALYSIS_OK[label-annotation-only]: treatment is joined only after PCA coordinates are fixed;
# used for plot color, not for computing the embedding
pca_plot = pca_coords.merge(metadata[["sample_id", "treatment"]], on="sample_id")
"""


def test_label_in_blind_stage_flags_label_subscript(has_finding):
    assert has_finding(BAD, RULE, filename="blind_qc.py")


def test_label_in_blind_stage_flags_query(has_finding):
    assert has_finding(BAD_QUERY, RULE, filename="run_pca.py")


def test_label_in_blind_stage_passes_in_supervised_file(has_finding):
    assert not has_finding(GOOD_IN_SUPERVISED, RULE, filename="run_de.py")


def test_label_in_blind_stage_passes_non_label_column(has_finding):
    assert not has_finding(GOOD_NO_LABEL, RULE, filename="blind_qc.py")


def test_label_in_blind_stage_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE, filename="run_pca.py")


def test_label_in_blind_stage_ignores_substring_filenames_qc(has_finding):
    # `query_cache.py` contains "qc" as a substring but is not a QC file.
    assert not has_finding(BAD, RULE, filename="query_cache.py")


def test_label_in_blind_stage_ignores_substring_filenames_hvg(has_finding):
    # `shvg.py` contains "hvg" as a substring but is not an HVG selection file.
    assert not has_finding(BAD, RULE, filename="shvg.py")


def test_label_in_blind_stage_still_matches_token(has_finding):
    # `score_qc.py` has 'qc' as a distinct token — still in scope.
    assert has_finding(BAD, RULE, filename="score_qc.py")
