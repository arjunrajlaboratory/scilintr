"""Rule: implicit-file-selection — globs, mtime sorts, 'latest'/'old' filenames."""

from __future__ import annotations

RULE = "implicit-file-selection"

BAD_GLOB_LATEST = """
import glob
files = glob.glob("data/*.csv")
path = sorted(files)[-1]
"""

BAD_LATEST_LITERAL = """
import pandas as pd
counts = pd.read_csv("data/latest_counts.tsv")
"""

BAD_BACKUP_LITERAL = """
import pandas as pd
counts = pd.read_csv("data/counts_backup_old.tsv")
"""

GOOD = """
import pandas as pd
DATA_RELEASE = "rnaseq_release_2026_05_22"
counts = pd.read_csv(f"data/{DATA_RELEASE}/counts.tsv")
"""

WAIVED = """
import pandas as pd
# ANALYSIS_OK[file-selection]: latest_counts.tsv is a stable symlink maintained by data registry;
# input fingerprint checked immediately below
counts = pd.read_csv("data/latest_counts.tsv")
"""


def test_implicit_file_selection_flags_glob_latest(has_finding):
    assert has_finding(BAD_GLOB_LATEST, RULE)


def test_implicit_file_selection_flags_latest_literal(has_finding):
    assert has_finding(BAD_LATEST_LITERAL, RULE)


def test_implicit_file_selection_flags_backup_literal(has_finding):
    assert has_finding(BAD_BACKUP_LITERAL, RULE)


def test_implicit_file_selection_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_implicit_file_selection_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


DOCSTRING_WITH_PREVIOUSLY = '''
"""Shared helpers across the data-loading layer.

This module centralizes routines that were previously duplicated across
several call sites and the loaders for old release files.
"""

import pandas as pd
'''


SENTENCE_WITH_LATEST = '''
"""Returns the most recent revision. Always picks the latest available
record from the registry."""
def get_latest(): pass
'''


def test_implicit_file_selection_skips_module_docstring(has_finding):
    # 'previously' / 'old' appear in a docstring sentence, not a file path.
    assert not has_finding(DOCSTRING_WITH_PREVIOUSLY, RULE)


def test_implicit_file_selection_skips_prose_with_latest(has_finding):
    assert not has_finding(SENTENCE_WITH_LATEST, RULE)
