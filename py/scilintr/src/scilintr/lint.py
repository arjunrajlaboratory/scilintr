"""Lint entry points — scaffold.

`lint_file(path)` and `lint_project(root)` mirror the R API. Rule
implementations are not yet wired in.
"""
from __future__ import annotations

from pathlib import Path

from .finding import Finding


def lint_file(path: str | Path, config: dict | None = None) -> list[Finding]:
    """Stub. Rule dispatch goes here once `per_file_linters` is populated."""
    return []


def lint_project(root: str | Path = ".", config: dict | None = None) -> list[Finding]:
    """Stub. Walks `*.py` files, builds project index, runs cross-file rules."""
    return []
