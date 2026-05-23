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


def test_bare_generated_macro_skips_inside_label(has_finding, wrap_body):
    """Self-review bug: scanner did not consult doc.in_prose, so
    structural-arg uses (\\label{sec:\\NSamples...}) fired even though
    the prose mask zeroes those regions for every other rule."""
    src = wrap_body(r"See \label{sec:n=\NSamples-cohort} for the QC pipeline.")
    assert not has_finding(src, RULE)


def test_bare_generated_macro_skips_inside_cite(has_finding, wrap_body):
    src = wrap_body(r"As reported by \citet{study\NSamples}, the effect held.")
    assert not has_finding(src, RULE)
