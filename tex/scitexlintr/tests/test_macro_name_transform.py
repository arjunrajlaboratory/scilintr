"""Tests for the id → macro name transform.

The spec lives in scitexlintr_readme_sketch.md and ``latex_report_values_strategy.md``.
These tests pin the transform so an upstream renderer that follows the
same spec produces matching names.
"""

from __future__ import annotations

import pytest

from scitexlintr._manifest import id_to_macro_name


@pytest.mark.parametrize(
    "manifest_id, expected",
    [
        # Simple keys
        ("n_samples", "NSamples"),
        ("n_control", "NControl"),
        ("samples", "Samples"),
        # Short letter segments uppercase as acronyms
        ("fdr_threshold", "FDRThreshold"),
        ("n_de_genes", "NDEGenes"),
        # Namespaced ids: split on '.', ':', or '/'
        ("diff-expr.n_samples", "NSamples"),
        ("diff-expr:n_replicates", "NReplicates"),
        ("path/to/n_samples", "NSamples"),
        # The acronym rule (≤3-letter segment uppercased) applies uniformly,
        # so ``ns`` (likely "namespace") goes to NS, not Ns. This is the
        # documented transform — callers that dislike it should rename the key.
        ("weird_ns_n_replicates", "WeirdNSNReplicates"),
        # Multi-level namespaces use the last segment
        ("a.b.c.n_samples", "NSamples"),
        # Digit segments map to English words digit-by-digit
        ("n_de_genes_fdr_0_05", "NDEGenesFDRZeroZeroFive"),
        ("year_2026", "YearTwoZeroTwoSix"),
        # Empty / odd inputs degrade gracefully
        ("", ""),
        ("_x", "X"),
        ("a__b", "AB"),
    ],
)
def test_id_to_macro_name(manifest_id, expected):
    assert id_to_macro_name(manifest_id) == expected
