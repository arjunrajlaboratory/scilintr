"""Shared pytest helpers for scitexlintr.

Per-rule tests follow the same convention as py/scilintr/tests:

* ``test_<rule>_flags_bad_code`` — BAD source produces ≥1 finding for the rule.
* ``test_<rule>_passes_good_code`` — GOOD equivalent produces 0 findings.
* ``test_<rule>_respects_waiver`` — BAD source preceded by
  ``% ANALYSIS_OK[<category>]:`` produces 0 findings.

The fixtures here wrap ``lint_tex`` with sensible defaults so each rule
file stays focused on the patterns it cares about.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest

from scitexlintr import Finding, lint_tex, parse_manifest


# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------

DEFAULT_MANIFEST_JSON = {
    "numbers": [
        {
            "id": "diff-expr.n_samples",
            "value": 48,
            "label_canonical": "number of cells passing QC",
            "label_aliases_forbidden": ["total cells", "total barcodes"],
        },
        {"id": "diff-expr.n_de_genes", "value": 317},
        {"id": "diff-expr.fdr_threshold", "value": 0.05},
        {"id": "diff-expr.contrast_phrase", "value": "treated versus control"},
        {
            "id": "diff-expr.exact_accuracy",
            "value": 0.973,
            "label_canonical": "exact match accuracy",
            "label_aliases_forbidden": ["accuracy"],
        },
        {"id": "diff-expr:n_replicates", "value": 12},
    ],
    "figures": [
        {"id": "volcano", "path": "figures/volcano_de.pdf", "sha256": "deadbeef"},
    ],
    "terms": [
        {
            "id": "BCLRT",
            "expansion": "branch-coherency log-likelihood ratio test",
            "overloaded_warning": "Not a Wilks-sense LRT; threshold 10 corresponds to Wilks 20.",
        },
    ],
}


@pytest.fixture
def manifest():
    return parse_manifest(DEFAULT_MANIFEST_JSON)


@pytest.fixture
def lint(manifest) -> Callable[..., list[Finding]]:
    def _lint(source: str, *, filename: str = "test.tex", **kwargs) -> list[Finding]:
        kwargs.setdefault("manifest", manifest)
        return lint_tex(source, filename=filename, **kwargs)

    return _lint


@pytest.fixture
def has_finding(lint) -> Callable[..., bool]:
    def _has(source: str, rule: str, **kwargs) -> bool:
        return any(f.rule == rule for f in lint(source, **kwargs))

    return _has


@pytest.fixture
def findings_for(lint) -> Callable[..., list[Finding]]:
    def _fl(source: str, rule: str, **kwargs) -> list[Finding]:
        return [f for f in lint(source, **kwargs) if f.rule == rule]

    return _fl


# ---------------------------------------------------------------------------
# Standard wrapping of small fragments inside a minimal document.
# ---------------------------------------------------------------------------

PREAMBLE = r"""
\documentclass{article}
\newcommand{\SciVal}[2]{#1}
\newcommand{\SciText}[2]{#1}
\newcommand{\NSamples}{48}
\newcommand{\NDEGenes}{317}
\newcommand{\FDRThreshold}{0.05}
\newcommand{\ContrastPhrase}{treated versus control}
\newcommand{\NReplicates}{12}
\newcommand{\ExactAccuracy}{0.973}
\begin{document}
"""

POSTAMBLE = "\n\\end{document}\n"


def wrap(body: str) -> str:
    """Wrap a body fragment in a minimal document — keeps per-rule snippets compact."""
    return PREAMBLE + body + POSTAMBLE


@pytest.fixture
def wrap_body():
    return wrap


# ---------------------------------------------------------------------------
# Corpus fixture
# ---------------------------------------------------------------------------

CORPUS_DIR = Path(__file__).parent / "data"


@pytest.fixture
def corpus_source() -> str:
    return (CORPUS_DIR / "report.tex").read_text()


@pytest.fixture
def corpus_manifest():
    return parse_manifest(json.loads((CORPUS_DIR / "manifest.json").read_text()))
