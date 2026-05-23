"""Rule registry."""

from __future__ import annotations

from scitexlintr._rules._base import Rule
from scitexlintr._rules.bare_generated_macro import rule as bare_generated_macro
from scitexlintr._rules.forbidden_alias import rule as forbidden_alias
from scitexlintr._rules.handwritten_numeric_claim import rule as handwritten_numeric_claim
from scitexlintr._rules.overloaded_term_no_warning import rule as overloaded_term_no_warning
from scitexlintr._rules.raw_generated_value import rule as raw_generated_value
from scitexlintr._rules.snapshot_mismatch import rule as snapshot_mismatch
from scitexlintr._rules.thresholds import magic_rule as magic_tex_threshold
from scitexlintr._rules.thresholds import unwrapped_rule as unwrapped_threshold
from scitexlintr._rules.unfingerprinted_figure import rule as unfingerprinted_figure
from scitexlintr._rules.unsourced_numeric_token import rule as unsourced_numeric_token

ALL_RULES: list[Rule] = [
    snapshot_mismatch,
    raw_generated_value,
    bare_generated_macro,
    unwrapped_threshold,
    unfingerprinted_figure,
    unsourced_numeric_token,
    overloaded_term_no_warning,
    forbidden_alias,
    handwritten_numeric_claim,
    magic_tex_threshold,
]
