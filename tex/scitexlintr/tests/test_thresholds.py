"""Rules: unwrapped-threshold and magic-tex-threshold."""

from __future__ import annotations

UNWRAPPED = "unwrapped-threshold"
MAGIC = "magic-tex-threshold"


def test_unwrapped_threshold_flags_manifest_value(has_finding, wrap_body):
    src = wrap_body("We used FDR $< 0.05$ as the cutoff.")
    assert has_finding(src, UNWRAPPED)


def test_unwrapped_threshold_passes_wrapped(has_finding, wrap_body):
    src = wrap_body(r"We used FDR $< \SciVal{\FDRThreshold}{0.05}$ as the cutoff.")
    assert not has_finding(src, UNWRAPPED)


def test_unwrapped_threshold_handles_le_macro(has_finding, wrap_body):
    src = wrap_body(r"We used FDR $\le 0.05$ as the cutoff.")
    assert has_finding(src, UNWRAPPED)


def test_magic_threshold_flags_non_manifest_value(has_finding, wrap_body):
    src = wrap_body(r"Using a relaxed cutoff $< 0.01$, we found more candidates.")
    assert has_finding(src, MAGIC)


def test_magic_threshold_does_not_fire_for_manifest_value(has_finding, wrap_body):
    # 0.05 is in the manifest; unwrapped-threshold fires instead.
    src = wrap_body(r"We used FDR $< 0.05$ as the cutoff.")
    assert not has_finding(src, MAGIC)


def test_unwrapped_threshold_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[unwrapped-threshold]: legacy text duplicated for reviewer reference\n"
        r"We used FDR $< 0.05$ as the cutoff."
    )
    assert not has_finding(src, UNWRAPPED)
