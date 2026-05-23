"""Rule: snapshot-mismatch."""

from __future__ import annotations

RULE = "snapshot-mismatch"


def test_snapshot_mismatch_flags_drifted_int(has_finding, wrap_body):
    src = wrap_body(r"We saw \SciVal{\NSamples}{47} cells.")
    assert has_finding(src, RULE)


def test_snapshot_mismatch_flags_drifted_text(has_finding, wrap_body):
    src = wrap_body(
        r"For the \SciText{\ContrastPhrase}{control versus treated} comparison."
    )
    assert has_finding(src, RULE)


def test_snapshot_mismatch_passes_matching_int(has_finding, wrap_body):
    src = wrap_body(r"We saw \SciVal{\NSamples}{48} cells.")
    assert not has_finding(src, RULE)


def test_snapshot_mismatch_passes_matching_float(has_finding, wrap_body):
    src = wrap_body(r"FDR $< \SciVal{\FDRThreshold}{0.05}$.")
    assert not has_finding(src, RULE)


def test_snapshot_mismatch_passes_matching_text(has_finding, wrap_body):
    src = wrap_body(
        r"For the \SciText{\ContrastPhrase}{treated versus control} comparison."
    )
    assert not has_finding(src, RULE)


def test_snapshot_mismatch_respects_waiver(has_finding, wrap_body):
    src = wrap_body(
        "% ANALYSIS_OK[snapshot-mismatch]: snapshot intentionally pre-update for review\n"
        r"We saw \SciVal{\NSamples}{47} cells."
    )
    assert not has_finding(src, RULE)


def test_snapshot_mismatch_carries_fix(lint, wrap_body):
    src = wrap_body(r"We saw \SciVal{\NSamples}{47} cells.")
    findings = [f for f in lint(src) if f.rule == RULE]
    assert findings and findings[0].fix is not None
    assert findings[0].fix.replacement == "48"


def test_snapshot_mismatch_skips_null_manifest_value(wrap_body):
    """Self-review bug: --write rewrote stale snapshots to literal
    'None' when the manifest value was JSON null. Behavior: don't fire
    at all (there's no value to match against)."""
    from scitexlintr import apply_fixes, lint_tex, parse_manifest

    manifest = parse_manifest({"numbers": [{"id": "sentinel", "value": None}]})
    src = wrap_body(r"We saw \SciVal{\Sentinel}{42} cells.")
    findings = lint_tex(src, filename="t.tex", manifest=manifest)
    rules = [f.rule for f in findings]
    assert "snapshot-mismatch" not in rules, (
        f"must not fire on null manifest values; got {rules}"
    )
    # And --write must not introduce a literal 'None'.
    new_src, _ = apply_fixes(src, findings)
    assert "None" not in new_src, f"--write inserted 'None': {new_src!r}"
