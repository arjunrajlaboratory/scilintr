"""Rule: duplicate-parameter-source — same parameter declared with different defaults in two places.

When the CLI default and a module-level constant disagree on the same parameter,
the effective value depends on which path the invocation takes. Two co-existing
sources of truth — neither is wrong, but consumers of either may report
incomparable results without knowing it.
"""

from __future__ import annotations

RULE = "duplicate-parameter-source"

BAD = """
import argparse

BATCH_SIZE = 32

parser = argparse.ArgumentParser()
parser.add_argument("--batch-size", type=int, default=128)
"""

GOOD = """
import argparse

BATCH_SIZE = 32

parser = argparse.ArgumentParser()
parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
"""

WAIVED = """
import argparse

BATCH_SIZE = 32

parser = argparse.ArgumentParser()
# ANALYSIS_OK[duplicate-config-source]: 32 is the dev override; production reads from CLI;
# divergence intentional until config refactor lands
parser.add_argument("--batch-size", type=int, default=128)
"""


def test_duplicate_parameter_source_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_duplicate_parameter_source_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_duplicate_parameter_source_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


# ---------------------------------------------------------------------------
# Cross-file detection (engine.lint_paths)
# ---------------------------------------------------------------------------


def test_cross_file_flags_conflicting_defaults(tmp_path):
    """A module-level constant in one file and a different default for the
    corresponding CLI flag in a sibling script. Each script in isolation looks
    fine; together they're not.
    """
    from scilintr import lint_paths

    (tmp_path / "config.py").write_text("BATCH_SIZE = 32\n")
    (tmp_path / "run_sweep.py").write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--batch-size', type=int, default=128)\n"
        "args = parser.parse_args()\n"
        "print(args.batch_size)\n"
    )

    findings = lint_paths([str(tmp_path)])
    dup = [f for f in findings if f.rule == RULE]
    assert dup, "expected a cross-file duplicate-parameter-source finding"
    files_involved = {f.filename for f in dup}
    assert any("config.py" in p or "run_sweep.py" in p for p in files_involved), (
        f"expected finding to cite one of the involved files, got: {files_involved}"
    )


def test_cross_file_passes_when_values_match(tmp_path):
    from scilintr import lint_paths

    (tmp_path / "config.py").write_text("BATCH_SIZE = 128\n")
    (tmp_path / "run_sweep.py").write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--batch-size', type=int, default=128)\n"
        "args = parser.parse_args()\n"
        "print(args.batch_size)\n"
    )

    findings = lint_paths([str(tmp_path)])
    dup = [f for f in findings if f.rule == RULE]
    assert not dup, f"defaults match across files; expected no finding, got {dup}"


def test_cross_file_passes_when_only_one_source(tmp_path):
    """A constant defined in one file but never referenced (and no sibling
    argparse declaring the same stem) is not a conflict."""
    from scilintr import lint_paths

    (tmp_path / "config.py").write_text("BATCH_SIZE = 32\n")
    (tmp_path / "other.py").write_text("FDR_THRESHOLD = 0.05\n")

    findings = lint_paths([str(tmp_path)])
    dup = [f for f in findings if f.rule == RULE]
    assert not dup, f"no cross-file conflict here; got {dup}"


def test_cross_file_respects_waiver(tmp_path):
    from scilintr import lint_paths

    (tmp_path / "config.py").write_text("BATCH_SIZE = 32\n")
    (tmp_path / "run_sweep.py").write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "# ANALYSIS_OK[duplicate-config-source]: dev sandbox; production reads from config.py\n"
        "parser.add_argument('--batch-size', type=int, default=128)\n"
        "args = parser.parse_args()\n"
        "print(args.batch_size)\n"
    )

    findings = lint_paths([str(tmp_path)])
    dup = [f for f in findings if f.rule == RULE]
    assert not dup, f"waiver should suppress cross-file finding, got {dup}"
