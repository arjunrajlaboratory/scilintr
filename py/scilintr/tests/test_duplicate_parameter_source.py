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


# ---------------------------------------------------------------------------
# Directory-scoped comparison (issue #5): a constant name that recurs across
# *independent analyses* (different directories) with different values is NOT a
# shared source of truth and must not be reconciled. The comparison is scoped to
# files sharing a directory.
# ---------------------------------------------------------------------------


def test_cross_file_does_not_compare_across_directories(tmp_path):
    """Two independent analyses in separate directories that happen to share a
    constant name with different values are not a conflict — there is no shared
    source of truth between them."""
    from scilintr import lint_paths

    audit = tmp_path / "A0.2-hub-audit"
    leaderboard = tmp_path / "A1.1-centrality-leaderboard"
    audit.mkdir()
    leaderboard.mkdir()
    (audit / "run.py").write_text("TOP_N = 100\n")
    (leaderboard / "run.py").write_text("TOP_N = 50\n")

    findings = lint_paths([str(tmp_path)])
    dup = [f for f in findings if f.rule == RULE]
    assert not dup, (
        f"independent analyses sharing a constant name is not a conflict, got {dup}"
    )


def test_cross_file_flags_conflict_within_same_directory(tmp_path):
    """Within one analysis directory, a constant that disagrees across sibling
    scripts IS a genuine conflict — e.g. the projections run would use a different
    null than the primary run, silently breaking an apples-to-apples comparison."""
    from scilintr import lint_paths

    analysis = tmp_path / "A1.2-leiden-communities"
    analysis.mkdir()
    (analysis / "run.py").write_text("N_NULL = 3\n")
    (analysis / "run_projections.py").write_text(
        "import argparse\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--n-null', type=int, default=20)\n"
        "args = parser.parse_args()\n"
    )

    findings = lint_paths([str(tmp_path)])
    dup = [f for f in findings if f.rule == RULE]
    assert dup, "intra-directory drift within a single analysis should still be caught"


def test_cross_file_independent_analyses_do_not_drown_real_conflict(tmp_path):
    """A genuine within-analysis conflict survives even when an unrelated analysis
    in another directory reuses the same constant name with yet another value."""
    from scilintr import lint_paths

    analysis = tmp_path / "A1.2-leiden-communities"
    other = tmp_path / "A0.8-graph-metrics"
    analysis.mkdir()
    other.mkdir()
    (analysis / "run.py").write_text("N_NULL = 3\n")
    (analysis / "run_projections.py").write_text("N_NULL = 50\n")
    (other / "run.py").write_text("N_NULL = 20\n")

    findings = lint_paths([str(tmp_path)])
    dup = [f for f in findings if f.rule == RULE]
    # Exactly one conflict: the A1.2 intra-directory disagreement. The A0.8 reuse
    # is independent and must not create additional findings.
    assert len(dup) == 1, f"expected one intra-analysis conflict only, got {dup}"
    assert "A1.2-leiden-communities" in dup[0].filename
