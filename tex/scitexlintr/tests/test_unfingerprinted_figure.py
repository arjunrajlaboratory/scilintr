"""Rule: unfingerprinted-figure."""

from __future__ import annotations

RULE = "unfingerprinted-figure"


def test_unfingerprinted_figure_flags_unknown_path(has_finding, wrap_body):
    src = wrap_body(r"\includegraphics{figures/heatmap.pdf}")
    assert has_finding(src, RULE)


def test_unfingerprinted_figure_passes_known_path(has_finding, wrap_body):
    src = wrap_body(r"\includegraphics{figures/volcano_de.pdf}")
    assert not has_finding(src, RULE)


def test_unfingerprinted_figure_passes_known_path_with_options(has_finding, wrap_body):
    src = wrap_body(r"\includegraphics[width=0.6\textwidth]{figures/volcano_de.pdf}")
    assert not has_finding(src, RULE)


def test_unfingerprinted_figure_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[unfingerprinted-figure]: schematic illustration, not data\n"
        r"\includegraphics{figures/heatmap.pdf}"
    )
    assert not has_finding(src, RULE)
