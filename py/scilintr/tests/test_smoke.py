"""Smoke test — verifies the package imports cleanly. Real fixture-driven
tests will land alongside rule implementations."""
from scilintr import __version__
from scilintr.lint import lint_file, lint_project
from scilintr.finding import Finding


def test_version():
    assert __version__.startswith("0.")


def test_lint_file_stub_returns_empty():
    assert lint_file("nonexistent.py") == []


def test_lint_project_stub_returns_empty():
    assert lint_project(".") == []


def test_finding_format():
    f = Finding(file="a.py", line=5, rule="R030", message="silent tryCatch")
    assert "a.py:5 [R030/warning] silent tryCatch" in f.format()
