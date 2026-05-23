"""Rule: plot-side-effect-filter — filtering data inside plot-named functions/files."""

from __future__ import annotations

RULE = "plot-side-effect-filter"

BAD = """
import pandas as pd

def plot_volcano(df):
    plot_df = df[df["padj"] < 0.05]
    return plot_df.plot.scatter("logFC", "-log10padj")
"""

GOOD = """
import pandas as pd

def plot_volcano(df):
    return df.plot.scatter("logFC", "-log10padj")
"""

WAIVED = """
import pandas as pd

FDR_THRESHOLD = 0.05

def plot_volcano(df):
    # ANALYSIS_OK[plot-filter]: only labels are filtered; does not affect the upstream DE results
    plot_df = df[df["padj"] < FDR_THRESHOLD]
    return plot_df.plot.scatter("logFC", "-log10padj")
"""


def test_plot_side_effect_filter_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE, filename="plotting.py")


def test_plot_side_effect_filter_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE, filename="plotting.py")


def test_plot_side_effect_filter_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE, filename="plotting.py")
