"""Rule: unsourced-numeric-token (and its many context heuristics)."""

from __future__ import annotations

RULE = "unsourced-numeric-token"


def test_unsourced_flags_isolated_number(has_finding, wrap_body):
    src = wrap_body("The coverage was 99.9 across runs.")
    assert has_finding(src, RULE)


def test_unsourced_passes_manifest_value(has_finding, wrap_body):
    # 317 IS in the manifest; raw-generated-value fires instead.
    src = wrap_body("The 317 differentially expressed genes cluster.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_section_reference(has_finding, wrap_body):
    src = wrap_body("See Section 4.2 for the QC pipeline.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_figure_reference(has_finding, wrap_body):
    src = wrap_body("See Figure 3 for the volcano plot.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_parenthesized_equation_reference(has_finding, wrap_body):
    """Self-review bug: ``Equation (5)`` falls through the reference
    heuristic because '(' isn't an alpha/dot, and the keyword walk-back
    never starts."""
    src = wrap_body("Recall Equation (5) and substitute the closure threshold.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_tilde_bracketed_figure_reference(has_finding, wrap_body):
    src = wrap_body(r"As shown in Fig.~(3), the variance decreases.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_percentage(has_finding, wrap_body):
    src = wrap_body(r"We recovered roughly 50\% of the input reads.")
    assert not has_finding(src, RULE)


def test_unsourced_flags_spelled_out_percent(has_finding, wrap_body):
    # Spelled-out percent IS a result claim; the typographic form is not.
    src = wrap_body("Coverage exceeded 99 percent across runs.")
    assert has_finding(src, RULE)


def test_unsourced_passes_threshold_context(has_finding, wrap_body):
    # Threshold context is owned by unwrapped-threshold / magic-tex-threshold.
    src = wrap_body(r"Using a relaxed cutoff $< 0.01$.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_le_threshold_context(has_finding, wrap_body):
    """Self-review bug: `<=` / `>=` were not recognized as threshold context,
    so unsourced double-fired with the threshold rules."""
    src = wrap_body(r"Using a stricter cutoff $<= 0.01$.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_ge_threshold_context(has_finding, wrap_body):
    src = wrap_body(r"Effect size $>= 0.5$ was treated as biologically meaningful.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_latex_leq_threshold_context(has_finding, wrap_body):
    src = wrap_body(r"With FDR $\leq 0.01$, only candidates beyond cutoff remain.")
    assert not has_finding(src, RULE)


def test_unsourced_passes_handwritten_context(has_finding, wrap_body):
    # handwritten-numeric-claim owns ``n = 23`` etc.
    src = wrap_body("We saw n = 23 in earlier work.")
    assert not has_finding(src, RULE)


def test_unsourced_skips_negative_when_manifest_has_negative(wrap_body):
    """Self-review bug: _NUMBER_RE captured only the digits, so a negative
    manifest value like -0.015 fired raw-generated-value on '-0.015' AND
    unsourced on '0.015' (sign-stripped, not in manifest). Two findings
    for one fact."""
    from scitexlintr import lint_tex, parse_manifest

    manifest = parse_manifest({"numbers": [{"id": "delta", "value": -0.015}]})
    src = wrap_body("The effect was Delta = -0.015 below the threshold.")
    findings = lint_tex(src, filename="t.tex", manifest=manifest)
    rules = {f.rule for f in findings}
    assert "raw-generated-value" in rules, "raw must still fire"
    assert "unsourced-numeric-token" not in rules, (
        f"unsourced fired on sign-stripped '0.015' that the manifest covers; rules={rules}"
    )


def test_unsourced_flags_k_equals(has_finding, wrap_body):
    """Codex P2 (drift between rules): ``k = 2`` must be reported.

    A previous version suppressed it on the grounds that handwritten would
    catch it, but handwritten only fires on ``[nNpPrR]\\s*=``. The two
    rules now share a single regex (``HANDWRITTEN_PATTERN``) so this case
    falls through to unsourced as intended.
    """
    src = wrap_body("We picked k = 2 as the seed count.")
    assert has_finding(src, RULE)


def test_unsourced_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[unsourced-numeric-token]: legacy QC threshold from upstream\n"
        "The coverage was 99.9 across runs."
    )
    assert not has_finding(src, RULE)
