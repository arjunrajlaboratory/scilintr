"""Rules: return-none-on-missing-input spellings + opt-in return-none-on-empty-input (issue #9).

``return-none-on-missing-input`` (default-on) catches every file-existence
spelling of the guard — the ``.exists()`` method, ``os.path.exists`` /
``isfile`` / ``isdir`` (module call or bare import), and pathlib's
``is_file()`` / ``is_dir()`` — returning any degraded placeholder (shared
with the silent-fallback-value rules via ``is_degraded_default``).

``return-none-on-empty-input`` is the broader, higher-FP sibling —
``is None`` / ``len(x) == 0`` / ``not x`` / ``df.empty`` guards. Optional
parameters routinely legitimately short-circuit on ``None``, so it is
opt-in: it runs only when named in ``rules=``/``--rules``.
"""

from __future__ import annotations

import pytest

from scilintr import lint_code

MISSING = "return-none-on-missing-input"
EMPTY = "return-none-on-empty-input"


def _guard(test: str, ret: str = "return None", prelude: str = "import os") -> str:
    return f"""
{prelude}

def load(p):
    if {test}:
        {ret}
    return read(p)
"""


# -------------------- missing-input: file-existence spellings --------------------


@pytest.mark.parametrize(
    "test, prelude",
    [
        ("not p.exists()", "from pathlib import Path"),
        ("not os.path.exists(p)", "import os"),
        ("not os.path.isfile(p)", "import os"),
        ("not os.path.isdir(p)", "import os"),
        ("not p.is_file()", "from pathlib import Path"),
        ("not p.is_dir()", "from pathlib import Path"),
        ("not isfile(p)", "from os.path import isfile"),
        ("not exists(p)", "from os.path import exists"),
        ("not osp.isfile(p)", "import os.path as osp"),
    ],
)
def test_missing_input_flags_existence_spellings(has_finding, test, prelude):
    assert has_finding(_guard(test, prelude=prelude), MISSING)


@pytest.mark.parametrize("ret", ["return", "return None", "return []", "return {}", "return 0", "return float('nan')"])
def test_missing_input_flags_degraded_returns(has_finding, ret):
    assert has_finding(_guard("not os.path.isfile(p)", ret=ret), MISSING)


def test_missing_input_passes_raise(has_finding):
    assert not has_finding(_guard("not os.path.isfile(p)", ret="raise FileNotFoundError(p)"), MISSING)


def test_missing_input_passes_real_fallback_value(has_finding):
    assert not has_finding(_guard("not os.path.isfile(p)", ret="return read(DEFAULT_PATH)"), MISSING)


def test_missing_input_passes_false_return(has_finding):
    # A predicate answering "is it there?" legitimately returns False.
    assert not has_finding(_guard("not os.path.isfile(p)", ret="return False"), MISSING)


def test_missing_input_ignores_unrelated_negated_call(has_finding):
    assert not has_finding(_guard("not validate(p)"), MISSING)


def test_missing_input_respects_waiver(has_finding):
    src = """
import os

def load(p):
    if not os.path.isfile(p):
        # ANALYSIS_OK[optional-input]: absent shard means 'not yet run'; caller filters None
        return None
    return read(p)
"""
    assert not has_finding(src, MISSING)


def test_missing_input_does_not_fire_on_empty_guards(has_finding):
    # The broad guards belong to the opt-in sibling only.
    assert not has_finding(_guard("df is None"), MISSING)


# -------------------- empty-input: opt-in --------------------


EMPTY_GUARDS = [
    "df is None",
    "len(records) == 0",
    "0 == len(records)",
    "len(records) < 1",
    "not len(records)",
    "not records",
    "not self.records",
    "df.empty",
]


@pytest.mark.parametrize("test", EMPTY_GUARDS)
def test_empty_input_flags_guards_when_selected(test):
    findings = lint_code(_guard(test), rules=[EMPTY])
    assert any(f.rule == EMPTY for f in findings)


@pytest.mark.parametrize("test", EMPTY_GUARDS)
def test_empty_input_is_off_by_default(has_finding, test):
    assert not has_finding(_guard(test), EMPTY)


def test_empty_input_passes_raise():
    findings = lint_code(_guard("df is None", ret="raise ValueError('df required')"), rules=[EMPTY])
    assert not findings


@pytest.mark.parametrize("test", ["not df.empty", "df is not None", "len(records) > 0", "x == 0", "not validate(p)", "not p.exists()"])
def test_empty_input_passes_other_tests(test):
    findings = lint_code(_guard(test), rules=[EMPTY])
    assert not any(f.rule == EMPTY for f in findings)


def test_empty_input_respects_waiver():
    src = """
def merge(df):
    if df is None:
        # ANALYSIS_OK[optional-input]: df is an optional overlay; None means no overlay
        return None
    return downstream(df)
"""
    assert not lint_code(src, rules=[EMPTY])


def test_lint_paths_honours_opt_in(tmp_path):
    from scilintr import lint_paths

    f = tmp_path / "a.py"
    f.write_text(_guard("df is None"))
    assert not any(x.rule == EMPTY for x in lint_paths([str(tmp_path)]))
    assert any(x.rule == EMPTY for x in lint_paths([str(tmp_path)], rules=[EMPTY]))


def test_cli_enable_adds_opt_in_rule_to_defaults(tmp_path, capsys):
    from scilintr.cli import main

    f = tmp_path / "a.py"
    f.write_text(_guard("df is None") + "\ntry:\n    x()\nexcept Exception:\n    pass\n")
    main([str(f)])
    default_out = capsys.readouterr().out
    assert EMPTY not in default_out and "silent-pass" in default_out
    main(["--enable", EMPTY, str(f)])
    enabled_out = capsys.readouterr().out
    assert EMPTY in enabled_out and "silent-pass" in enabled_out
