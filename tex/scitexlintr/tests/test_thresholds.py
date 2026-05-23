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


def test_unwrapped_threshold_recognizes_scientific_notation(wrap_body):
    """Codex re-review P1: ``_THRESHOLD_RE`` num group was \\d+(?:\\.\\d+)?,
    so ``p < 1e-8`` parsed as threshold ``1`` and either misfired
    magic-tex-threshold on ``1`` or missed the real value entirely."""
    from scitexlintr import lint_tex, parse_manifest

    manifest = parse_manifest({"numbers": [{"id": "alpha", "value": 1e-8}]})
    src = wrap_body(r"With $p < 1e-8$, the result was strongly significant.")
    findings = lint_tex(src, filename="t.tex", manifest=manifest)
    rules = {(f.rule, "1" in f.message and "1e-8" not in f.message) for f in findings}
    assert any(f.rule == "unwrapped-threshold" and "1e-8" in f.message for f in findings), (
        f"unwrapped-threshold did not see '1e-8' as the threshold; findings: "
        f"{[(f.rule, f.message[:80]) for f in findings]}"
    )
    # Must NOT fire magic-tex-threshold on the bogus '1' parsed from '1e-8'.
    assert not any(
        f.rule == "magic-tex-threshold" and "threshold 1 " in f.message for f in findings
    )


def test_unwrapped_threshold_handles_string_manifest_value(wrap_body):
    """Self-review bug: values_equal_as_snapshot exact-compared str-typed
    manifest values, so a manifest entry stored as the string ``'0.0500'``
    (not a JSON number) failed to match ``'0.05'`` in prose. unwrapped
    silently fell through to magic-tex-threshold (error → warning)."""
    from scitexlintr import lint_tex, parse_manifest

    manifest = parse_manifest({"numbers": [{"id": "alpha", "value": "0.0500"}]})
    src = wrap_body(r"With FDR $< 0.05$, we identified the candidates.")
    findings = lint_tex(src, filename="t.tex", manifest=manifest)
    rules = {f.rule for f in findings}
    assert UNWRAPPED in rules, (
        f"string-typed manifest value didn't match numerically; rules={rules}"
    )
    assert MAGIC not in rules, "magic should not fire when manifest has the value"


def test_unwrapped_threshold_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[unwrapped-threshold]: legacy text duplicated for reviewer reference\n"
        r"We used FDR $< 0.05$ as the cutoff."
    )
    assert not has_finding(src, UNWRAPPED)
