"""Rule registry — import each rule module and append to ALL_RULES."""

from __future__ import annotations

from scilintr._rules._base import CrossFileRule, Rule
from scilintr._rules.ambiguous_layer_access import rule as ambiguous_layer_access
from scilintr._rules.broad_exception import rule as broad_exception
from scilintr._rules.hardcoded_design_formula import rule as hardcoded_design_formula
from scilintr._rules.hardcoded_sample_ids import rule as hardcoded_sample_ids
from scilintr._rules.implicit_file_selection import rule as implicit_file_selection
from scilintr._rules.label_in_blind_stage import rule as label_in_blind_stage
from scilintr._rules.magic_threshold import rule as magic_threshold
from scilintr._rules.positional_metadata_access import rule as positional_metadata_access
from scilintr._rules.positional_sample_alignment import rule as positional_sample_alignment
from scilintr._rules.return_none_on_missing_input import rule as return_none_on_missing_input
from scilintr._rules.silent_fallback_return import rule as silent_fallback_return
from scilintr._rules.silent_pass import rule as silent_pass
from scilintr._rules.silent_stub_fallback import rule as silent_stub_fallback
from scilintr._rules.synthetic_data_generation import rule as synthetic_data_generation
from scilintr._rules.unannotated_filter import rule as unannotated_filter
from scilintr._rules.unannotated_missingness import rule as unannotated_missingness
from scilintr._rules.duplicate_parameter_source import rule as duplicate_parameter_source
from scilintr._rules.duplicate_parameter_source_cross_file import (
    rule as duplicate_parameter_source_cross_file,
)
from scilintr._rules.plot_side_effect_filter import rule as plot_side_effect_filter
from scilintr._rules.runtime_assert import rule as runtime_assert
from scilintr._rules.sentinel_mask_assignment import rule as sentinel_mask_assignment
from scilintr._rules.unannotated_transform import rule as unannotated_transform
from scilintr._rules.unchecked_cache import rule as unchecked_cache
from scilintr._rules.unchecked_merge import rule as unchecked_merge
from scilintr._rules.unchecked_model_fit import rule as unchecked_model_fit
from scilintr._rules.unconsumed_cli_flag import rule as unconsumed_cli_flag
from scilintr._rules.unseeded_stochastic import rule as unseeded_stochastic
from scilintr._rules.unvalidated_config import rule as unvalidated_config
from scilintr._rules.warning_suppression import rule as warning_suppression

ALL_RULES: list[Rule] = [
    broad_exception,
    silent_pass,
    silent_stub_fallback,
    silent_fallback_return,
    return_none_on_missing_input,
    positional_metadata_access,
    magic_threshold,
    unchecked_merge,
    positional_sample_alignment,
    unannotated_filter,
    unannotated_missingness,
    implicit_file_selection,
    unchecked_cache,
    synthetic_data_generation,
    unseeded_stochastic,
    label_in_blind_stage,
    hardcoded_design_formula,
    unannotated_transform,
    ambiguous_layer_access,
    hardcoded_sample_ids,
    warning_suppression,
    unchecked_model_fit,
    plot_side_effect_filter,
    unconsumed_cli_flag,
    duplicate_parameter_source,
    runtime_assert,
    unvalidated_config,
    sentinel_mask_assignment,
]

ALL_CROSS_FILE_RULES: list[CrossFileRule] = [
    duplicate_parameter_source_cross_file,
]
