"""Rule: bare-generated-macro."""

from __future__ import annotations

RULE = "bare-generated-macro"


def test_bare_generated_macro_flags_unwrapped(has_finding, wrap_body):
    src = wrap_body(r"Without wrapper, \NSamples samples were retained.")
    assert has_finding(src, RULE)


def test_bare_generated_macro_passes_wrapped(has_finding, wrap_body):
    src = wrap_body(r"With wrapper, \SciVal{\NSamples}{48} samples were retained.")
    assert not has_finding(src, RULE)


def test_bare_generated_macro_passes_text_wrapper(has_finding, wrap_body):
    src = wrap_body(
        r"For \SciText{\ContrastPhrase}{treated versus control} we ran ..."
    )
    assert not has_finding(src, RULE)


def test_bare_generated_macro_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[bare-generated-macro]: title macro intentionally expanded inline\n"
        r"Without wrapper, \NSamples samples were retained."
    )
    assert not has_finding(src, RULE)
