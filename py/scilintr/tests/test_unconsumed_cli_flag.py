"""Rule: unconsumed-cli-flag — argparse flag declared but the parsed attribute is never read.

Two common shapes in the wild:

* a flag is added to the parser but the receiving function's signature has no
  matching parameter, so the value never reaches the consumer;
* a boolean flag is parsed and stored on ``args`` but no code path inspects it,
  so the underlying behavior runs unconditionally.
"""

from __future__ import annotations

RULE = "unconsumed-cli-flag"

BAD = """
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--run-id", type=int, default=1)
parser.add_argument("--dataset", type=str)
args = parser.parse_args()

print(args.dataset)
"""

GOOD = """
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--run-id", type=int, default=1)
parser.add_argument("--dataset", type=str)
args = parser.parse_args()

process(args.dataset, run_id=args.run_id)
"""

WAIVED = """
import argparse

parser = argparse.ArgumentParser()
# ANALYSIS_OK[deprecated-flag]: --run-id is now read from the config file;
# kept for backward compatibility with shell scripts that still pass it
parser.add_argument("--run-id", type=int, default=1)
parser.add_argument("--dataset", type=str)
args = parser.parse_args()

print(args.dataset)
"""


def test_unconsumed_cli_flag_flags_bad_code(has_finding):
    assert has_finding(BAD, RULE)


def test_unconsumed_cli_flag_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unconsumed_cli_flag_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)


BAD_HIDDEN_BY_UNRELATED_ATTR = """
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--verbose", action="store_true")
parser.add_argument("--dataset", type=str)
args = parser.parse_args()

# Unrelated attribute access happens to share the name `verbose` —
# the flag is still un-consumed.
other_obj.verbose
print(args.dataset)
"""

NO_PARSE_ARGS = """
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--verbose", action="store_true")
# never calls parser.parse_args(); rule has no anchor to scope reads against
"""


def test_unconsumed_cli_flag_scopes_to_args_object(has_finding):
    # `other_obj.verbose` should not count as "args.verbose was read".
    assert has_finding(BAD_HIDDEN_BY_UNRELATED_ATTR, RULE)


def test_unconsumed_cli_flag_skips_when_no_parse_args(has_finding):
    # Without a parse_args() anchor we can't reliably scope reads → don't fire.
    assert not has_finding(NO_PARSE_ARGS, RULE)
