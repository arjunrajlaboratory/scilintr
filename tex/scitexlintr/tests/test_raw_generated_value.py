"""Rule: raw-generated-value."""

from __future__ import annotations

RULE = "raw-generated-value"


def test_raw_value_flags_bare_int_in_prose(has_finding, wrap_body):
    src = wrap_body("The 317 differentially expressed genes cluster into three groups.")
    assert has_finding(src, RULE)


def test_raw_value_flags_bare_phrase_in_prose(has_finding, wrap_body):
    src = wrap_body("We focused on treated versus control comparisons across batches.")
    assert has_finding(src, RULE)


def test_raw_value_passes_wrapped_int(has_finding, wrap_body):
    src = wrap_body(r"We observed \SciVal{\NDEGenes}{317} DE genes overall.")
    assert not has_finding(src, RULE)


def test_raw_value_passes_wrapped_text(has_finding, wrap_body):
    src = wrap_body(r"For \SciText{\ContrastPhrase}{treated versus control}, we ...")
    assert not has_finding(src, RULE)


def test_raw_value_word_boundary(has_finding, wrap_body):
    # 3175 should NOT match 317 (word boundary on the right).
    src = wrap_body("A neighboring transcript locus 3175 was excluded.")
    assert not has_finding(src, RULE)


def test_raw_value_matches_unpadded_scientific(wrap_body):
    """Self-review bug: ``repr(1e-8) == '1e-08'`` (zero-padded exponent),
    but prose conventionally writes ``1e-8``. Must find either form."""
    from scitexlintr import lint_tex, parse_manifest
    manifest = parse_manifest({"numbers": [{"id": "p_threshold", "value": 1e-8}]})
    src = wrap_body("With p = 1e-8, the result was strongly significant.")
    findings = lint_tex(src, filename="t.tex", manifest=manifest)
    assert any(f.rule == "raw-generated-value" for f in findings), (
        f"raw-generated-value missed '1e-8'; findings: {[(f.rule, f.line) for f in findings]}"
    )


def test_raw_value_flags_trailing_zero_float(has_finding, wrap_body):
    """``0.050`` in prose must match a manifest ``fdr_threshold = 0.05``.

    Exact-string matching missed this (``repr(0.05) == '0.05' != '0.050'``),
    and since the value *has* a manifest entry it also escaped
    unsourced-numeric-token — landing in neither rule. The detector now
    compares numerically, like snapshot-mismatch does."""
    src = wrap_body("We thresholded at a false-discovery rate of 0.050 throughout.")
    assert has_finding(src, RULE)


def test_raw_value_flags_higher_precision_float(has_finding, wrap_body):
    # 0.0500 (more trailing zeros) also equals fdr_threshold 0.05 numerically.
    src = wrap_body("The cutoff was 0.0500 by convention.")
    assert has_finding(src, RULE)


def test_raw_value_trailing_zero_still_respects_boundary(has_finding, wrap_body):
    # 0.051 is NOT equal to 0.05 — must not fire.
    src = wrap_body("A nearby value 0.051 was used elsewhere and is unrelated.")
    assert not has_finding(src, RULE)


def test_raw_value_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[raw-generated-value]: this 317 refers to the prior dataset\n"
        "The 317 differentially expressed genes cluster into three groups."
    )
    assert not has_finding(src, RULE)
