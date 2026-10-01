r"""Issue #14 — friction authoring a number-dense report.

1. ``unit``-bearing snapshot: ``\SciVal{\Frac}{96.5\%}`` (the rendered form)
   is as valid as ``{0.9653}`` (the stored value).
2. A ``\%``-suffixed literal is not the raw form of an integer count
   (``97.0\%`` coverage vs. a registered pair-count ``97``).
3. ``\SciVal{\UnknownMacro}{…}`` — a macro the manifest does not define —
   is ``unknown-value-id`` in TeX too (it would break ``pdflatex``).
4. Region waivers (``ANALYSIS_OK_BEGIN[rule]: …`` … ``ANALYSIS_OK_END[rule]``)
   and comma-separated rule lists in one waiver.
"""

from __future__ import annotations

import pytest

from scitexlintr import lint_html, lint_tex, parse_manifest
from scitexlintr._waivers import find_waivers, is_waived

MANIFEST = parse_manifest(
    {
        "numbers": [
            {"id": "frac_claims_dated", "value": 0.9653, "unit": "percent", "precision": 1},
            {"id": "mean_ratio", "value": 7.47712, "unit": "decimal", "precision": 2},
            {"id": "n_pairs", "value": 97},
            {"id": "fold_label", "value": 2.5, "display": r"2.5$\times$"},
            {"id": "coverage_pct", "value": 97.25},
        ]
    }
)

PRE = r"""\documentclass{article}
\newcommand{\SciVal}[2]{#1}
\newcommand{\SciText}[2]{#1}
\begin{document}
"""
POST = "\n\\end{document}\n"


def lint(body: str, **kw):
    kw.setdefault("manifest", MANIFEST)
    return lint_tex(PRE + body + POST, filename="t.tex", **kw)


def rules_of(body: str, **kw) -> list[str]:
    return [f.rule for f in lint(body, **kw)]


# -------------------- 1. rendered snapshot for unit-bearing entries --------------------


@pytest.mark.parametrize(
    "snapshot",
    [r"0.9653", r"96.5\%", r" 96.5\% ", r"96.50\%", r"96.5 \%", r"96.5\,\%", r"96.5~\%"],
)
def test_percent_snapshot_accepts_raw_or_rendered(snapshot):
    assert "snapshot-mismatch" not in rules_of(rf"\SciVal{{\FracClaimsDated}}{{{snapshot}}} dated.")


@pytest.mark.parametrize("snapshot", [r"96.6\%", r"96.5", r"97\%", r"0.97"])
def test_percent_snapshot_still_flags_wrong_values(snapshot):
    assert "snapshot-mismatch" in rules_of(rf"\SciVal{{\FracClaimsDated}}{{{snapshot}}} dated.")


def test_stale_rendered_snapshot_fix_keeps_rendered_style():
    from scitexlintr import apply_fixes

    src = PRE + r"\SciVal{\FracClaimsDated}{95.1\%} dated." + POST
    findings = [f for f in lint_tex(src, manifest=MANIFEST) if f.rule == "snapshot-mismatch"]
    assert len(findings) == 1 and r"96.5\%" in findings[0].message
    fixed, n = apply_fixes(src, findings)
    assert n == 1 and r"\SciVal{\FracClaimsDated}{96.5\%}" in fixed


def test_stale_raw_snapshot_fix_keeps_raw_style():
    from scitexlintr import apply_fixes

    src = PRE + r"\SciVal{\FracClaimsDated}{0.95} dated." + POST
    findings = [f for f in lint_tex(src, manifest=MANIFEST) if f.rule == "snapshot-mismatch"]
    fixed, n = apply_fixes(src, findings)
    assert n == 1 and r"\SciVal{\FracClaimsDated}{0.9653}" in fixed


def test_unrenderable_unit_reported_as_such():
    m = parse_manifest({"numbers": [{"id": "x", "value": 0.97, "unit": "pct"}]})
    found = [f for f in lint(r"\SciVal{\X}{97\%} x.", manifest=m) if f.rule == "snapshot-mismatch"]
    assert len(found) == 1
    assert "unsupported unit" in found[0].message
    assert found[0].fix is None


def test_decimal_snapshot_accepts_rendered():
    assert "snapshot-mismatch" not in rules_of(r"\SciVal{\MeanRatio}{7.48} mean.")
    assert "snapshot-mismatch" not in rules_of(r"\SciVal{\MeanRatio}{7.47712} mean.")
    assert "snapshot-mismatch" in rules_of(r"\SciVal{\MeanRatio}{7.5} mean.")


def test_display_snapshot_accepts_display_string():
    assert "snapshot-mismatch" not in rules_of(r"\SciVal{\FoldLabel}{2.5$\times$} fold.")
    assert "snapshot-mismatch" not in rules_of(r"\SciVal{\FoldLabel}{2.5} fold.")


# -------------------- 2. percent literal vs integer count --------------------


def _raw(body):
    return [f for f in lint(body) if f.rule == "raw-generated-value"]


@pytest.mark.parametrize("lit", [r"97.0\%", r"97\%", r"97 \%", r"97\,\%", r"97~\%"])
def test_percent_literal_vs_integer_count_is_only_a_warning(lit):
    found = _raw(rf"Coverage was {lit} of claims.")
    assert len(found) == 1
    assert found[0].severity == "warning"
    assert "coincidental" in found[0].message


def test_percent_literal_vs_integer_passes_fail_on_error_gate():
    assert all(f.severity != "error" for f in lint(r"Coverage was 97.0\% of claims."))


def test_bare_integer_still_matches_count():
    assert "raw-generated-value" in rules_of(r"We found 97 pairs.")


def test_percent_literal_still_matches_non_integer_value():
    # A float with no unit may itself be a stored percentage.
    assert "raw-generated-value" in rules_of(r"Coverage was 97.25\% of claims.")


def test_percent_literal_vs_integer_count_html():
    src = "<html><body><p>Coverage was 97.0% of claims; we found 97 pairs.</p></body></html>"
    found = [f for f in lint_html(src, manifest=MANIFEST) if f.rule == "raw-generated-value"]
    assert sorted(f.severity for f in found) == ["error", "warning"]  # bare 97 is the error


# -------------------- 3. unknown macro in a TeX wrapper --------------------


def test_unknown_macro_in_scival_flagged():
    found = [f for f in lint(r"We saw \SciVal{\NoSuchValue}{12} items.") if f.rule == "unknown-value-id"]
    assert len(found) == 1
    assert "NoSuchValue" in found[0].message


def test_unknown_macro_in_scitext_flagged():
    assert "unknown-value-id" in rules_of(r"The \SciText{\NoSuchPhrase}{foo} case.")


@pytest.mark.parametrize(
    "definition",
    [r"\newcommand{\LocalVal}{3}", r"\renewcommand*{\LocalVal}{3}", r"\providecommand\LocalVal{3}", r"\def\LocalVal{3}"],
)
def test_document_defined_macro_not_flagged(definition):
    src = PRE.replace(r"\begin{document}", definition + "\n\\begin{document}") + r"\SciVal{\LocalVal}{3} x." + POST
    assert not [f for f in lint_tex(src, manifest=MANIFEST) if f.rule == "unknown-value-id"]


def test_known_macro_not_flagged():
    assert "unknown-value-id" not in rules_of(r"\SciVal{\NPairs}{97} pairs.")


def test_unknown_macro_needs_manifest():
    assert "unknown-value-id" not in rules_of(r"\SciVal{\NoSuchValue}{12}", manifest=None)


def test_unknown_macro_waivable():
    body = "% ANALYSIS_OK[unknown-value-id]: macro defined in preamble.tex, not the manifest\n" \
        r"\SciVal{\NoSuchValue}{12} items."
    assert "unknown-value-id" not in rules_of(body)


# -------------------- 4. region waivers + multi-rule waivers --------------------


def test_region_waiver_covers_every_line_until_end():
    body = (
        "% ANALYSIS_OK_BEGIN[unsourced-numeric-token]: publication years in the narrative timeline\n"
        "In 2013 the first atlas appeared.\n\n\n\n\n\n"
        "By 2019 it had grown, and in 2026 it is standard.\n"
        "% ANALYSIS_OK_END[unsourced-numeric-token]\n"
        "In 2031 we expect more.\n"
    )
    found = [f for f in lint(body) if f.rule == "unsourced-numeric-token"]
    assert [f.line for f in found] == [PRE.count("\n") + 10]


def test_region_waiver_is_rule_scoped():
    body = (
        "% ANALYSIS_OK_BEGIN[unsourced-numeric-token]: years\n"
        "We found 97 pairs in 2013.\n"
        "% ANALYSIS_OK_END[unsourced-numeric-token]\n"
    )
    rules = rules_of(body)
    assert "unsourced-numeric-token" not in rules
    assert "raw-generated-value" in rules


def test_unclosed_region_waiver_waives_nothing():
    body = (
        "% ANALYSIS_OK_BEGIN[unsourced-numeric-token]: years\n"
        "\n\n\n\n\n"
        "In 2013 the first atlas appeared.\n"
    )
    assert "unsourced-numeric-token" in rules_of(body)


def test_region_waiver_requires_explanation():
    src = "% ANALYSIS_OK_BEGIN[unsourced-numeric-token]:\nx\n% ANALYSIS_OK_END[unsourced-numeric-token]\n"
    assert find_waivers(src) == []


def test_region_waiver_html():
    src = (
        "<html><body>\n"
        "<!-- ANALYSIS_OK_BEGIN[unsourced-numeric-token]: timeline years -->\n"
        "<p>In 2013</p>\n<p></p>\n<p></p>\n<p></p>\n<p></p>\n<p>and 2019</p>\n"
        "<!-- ANALYSIS_OK_END[unsourced-numeric-token] -->\n"
        "<p>then 2031</p>\n"
        "</body></html>\n"
    )
    found = [f for f in lint_html(src, manifest=MANIFEST) if f.rule == "unsourced-numeric-token"]
    assert [f.line for f in found] == [10]


def test_multi_rule_waiver():
    ws = find_waivers("% ANALYSIS_OK[raw-generated-value, unsourced-numeric-token]: legacy table\n")
    assert len(ws) == 1
    assert is_waived(2, "raw-generated-value", ws)
    assert is_waived(2, "unsourced-numeric-token", ws)
    assert not is_waived(2, "snapshot-mismatch", ws)


def test_multi_rule_waiver_end_to_end():
    body = "% ANALYSIS_OK[raw-generated-value,unsourced-numeric-token]: sourced from pairs.csv\n" \
        "We found 97 pairs in 2013.\n"
    rules = rules_of(body)
    assert "raw-generated-value" not in rules
    assert "unsourced-numeric-token" not in rules


def test_region_waiver_multi_rule():
    body = (
        "% ANALYSIS_OK_BEGIN[raw-generated-value,unsourced-numeric-token]: table from pairs.csv\n"
        "We found 97 pairs in 2013.\n"
        "% ANALYSIS_OK_END\n"
    )
    rules = rules_of(body)
    assert "raw-generated-value" not in rules
    assert "unsourced-numeric-token" not in rules


def test_waiver_after_a_second_percent_in_comment():
    ws = find_waivers("text % note %ANALYSIS_OK[raw-generated-value]: sourced from pairs.csv\n")
    assert len(ws) == 1 and ws[0].category == "raw-generated-value"


def test_js_region_waiver():
    from scitexlintr._html import prepare_html
    from scitexlintr._waivers import find_html_waivers

    src = (
        "<html><body><script>\n"
        "const u = 'http://example.org'; // ANALYSIS_OK_BEGIN[script-data-literal]: fixture data\n"
        "const a = [1,2,3];\n"
        "/* ANALYSIS_OK_END */\n"
        "</script></body></html>\n"
    )
    ws = find_html_waivers(prepare_html(src, filename="t.html"))
    assert len(ws) == 1 and ws[0].end_line == 4


def test_region_end_may_carry_trailing_text():
    src = "% ANALYSIS_OK_BEGIN[a]: why\nx\n% ANALYSIS_OK_END[a]: end of table 3\n% ANALYSIS_OK_BEGIN[b]: why\ny\n% ANALYSIS_OK_END: done\n"
    ws = find_waivers(src)
    assert sorted((w.category, w.line, w.end_line) for w in ws) == [("a", 1, 3), ("b", 4, 6)]


def test_named_end_closes_region_naming_all_its_rules():
    src = "% ANALYSIS_OK_BEGIN[a, b]: why\nx\n% ANALYSIS_OK_END[a]\n"
    ws = find_waivers(src)
    assert len(ws) == 1 and ws[0].end_line == 3
    assert is_waived(2, "b", ws)


def test_named_end_skips_regions_not_naming_it():
    src = "% ANALYSIS_OK_BEGIN[a]: outer\n% ANALYSIS_OK_BEGIN[b]: inner\nx\n% ANALYSIS_OK_END[a]\n"
    ws = find_waivers(src)
    assert [(w.category, w.end_line) for w in ws] == [("a", 4)]


def test_second_waiver_on_line_found_when_first_is_malformed():
    ws = find_waivers("text % ANALYSIS_OK_NOTE see below % ANALYSIS_OK[a]: why\n")
    assert [w.category for w in ws] == ["a"]


def test_percent_clash_does_not_hide_rendered_form_error():
    m = parse_manifest({"numbers": [
        {"id": "n_pairs", "value": 97},
        {"id": "frac", "value": 0.97, "unit": "percent", "precision": 1},
    ]})
    found = [f for f in lint(r"Coverage was 97.0\% of claims.", manifest=m) if f.rule == "raw-generated-value"]
    assert len(found) == 1
    assert found[0].severity == "error" and "id=frac" in found[0].message


@pytest.mark.parametrize(
    "definition",
    [r"\let\LocalVal\relax", r"\NewDocumentCommand{\LocalVal}{}{3}", r"\DeclareDocumentCommand\LocalVal{}{3}",
     "\\newcommand\n  {\\LocalVal}{3}"],
)
def test_more_document_definitions_not_flagged(definition):
    src = PRE.replace(r"\begin{document}", definition + "\n\\begin{document}") + r"\SciVal{\LocalVal}{3} x." + POST
    assert not [f for f in lint_tex(src, manifest=MANIFEST) if f.rule == "unknown-value-id"]


# -------------------- review round 2 --------------------


def _fix_of(src_body, manifest):
    from scitexlintr import apply_fixes

    src = PRE + src_body + POST
    found = [f for f in lint_tex(src, manifest=manifest) if f.rule == "snapshot-mismatch"]
    assert len(found) == 1
    fixed, n = apply_fixes(src, found)
    assert n == 1
    return fixed


def test_write_keeps_rendered_style_for_display_entry():
    m = parse_manifest({"numbers": [{"id": "pct_disp", "value": 0.5, "display": r"50\%"}]})
    assert r"\SciVal{\PCTDisp}{50\%}" in _fix_of(r"\SciVal{\PCTDisp}{40\%} x.", m)


def test_write_keeps_rendered_style_for_decimal_entry():
    assert r"\SciVal{\MeanRatio}{7.48}" in _fix_of(r"\SciVal{\MeanRatio}{7.40} x.", MANIFEST)


def test_write_keeps_raw_style_for_decimal_entry():
    assert r"\SciVal{\MeanRatio}{7.47712}" in _fix_of(r"\SciVal{\MeanRatio}{7.4} x.", MANIFEST)


def test_unrenderable_unit_stored_value_snapshot_passes_and_problem_reported_once():
    m = parse_manifest({"numbers": [{"id": "x", "value": 0.5, "unit": "pct"}]})
    found = [f for f in lint(r"\SciVal{\X}{0.5} a \SciVal{\X}{0.5} b \SciVal{\X}{0.4} c.", manifest=m)
             if f.rule == "snapshot-mismatch"]
    assert len(found) == 1 and "unsupported unit" in found[0].message


@pytest.mark.parametrize("snapshot", [r"9.65e1\%", r"0965e-1\%", r"096.5\%"])
def test_rendered_match_does_not_accept_arbitrary_numeric_spellings(snapshot):
    assert "snapshot-mismatch" in rules_of(rf"\SciVal{{\FracClaimsDated}}{{{snapshot}}} dated.")


@pytest.mark.parametrize(
    "definition",
    [r"\expandafter\newcommand\csname LocalVal\endcsname{3}", r"\csdef{LocalVal}{3}",
     r"\newrobustcmd{\LocalVal}{3}", r"\NewExpandableDocumentCommand{\LocalVal}{}{3}",
     r"\DeclareMathOperator{\LocalVal}{lv}", r"\newcommandx{\LocalVal}{3}"],
)
def test_even_more_document_definitions_not_flagged(definition):
    src = PRE.replace(r"\begin{document}", definition + "\n\\begin{document}") + r"\SciVal{\LocalVal}{3} x." + POST
    assert not [f for f in lint_tex(src, manifest=MANIFEST) if f.rule == "unknown-value-id"]


def test_macro_defined_in_input_file_not_flagged(tmp_path):
    from scitexlintr import lint_file

    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "macros.tex").write_text(r"\newcommand{\LocalVal}{3}" + "\n")
    main = tmp_path / "main.tex"
    main.write_text(PRE.replace(r"\begin{document}", "\\input{build/macros}\n\\begin{document}")
                    + r"\SciVal{\LocalVal}{3} x. \SciVal{\Gone}{1} y." + POST)
    import json
    mpath = tmp_path / "m.json"
    mpath.write_text(json.dumps({"numbers": [{"id": "n_pairs", "value": 97}]}))
    found = [f for f in lint_file(main, manifest_path=mpath) if f.rule == "unknown-value-id"]
    assert [("Gone" in f.message) for f in found] == [True]


def test_cli_pools_definitions_across_files(tmp_path, capsys):
    import json

    from scitexlintr.cli import main as cli_main

    (tmp_path / "main.tex").write_text(
        PRE.replace(r"\begin{document}", "\\newcommand{\\LocalCount}{12}\n\\begin{document}")
        + "\\input{chapter1}" + POST)
    (tmp_path / "chapter1.tex").write_text(r"We saw \SciVal{\LocalCount}{12} things." + "\n")
    mpath = tmp_path / "m.json"
    mpath.write_text(json.dumps({"numbers": [{"id": "n_pairs", "value": 97}]}))
    cli_main([str(tmp_path / "main.tex"), str(tmp_path / "chapter1.tex"),
              f"--manifest={mpath}", "--rules=unknown-value-id"])
    assert "unknown-value-id" not in capsys.readouterr().out


@pytest.mark.parametrize("end", [
    "% ANALYSIS_OK_END[a] end of table 3",
    "% ANALYSIS_OK_END [a]",
    "% ANALYSIS_OK_END -- done",
])
def test_region_end_free_text_forms(end):
    ws = find_waivers(f"% ANALYSIS_OK_BEGIN[a]: why\nx\n{end}\n")
    assert len(ws) == 1 and ws[0].end_line == 3


# -------------------- codex review --------------------


@pytest.mark.parametrize("inp", ["\\input macros", "\\input macros.tex", "\\input{macros}", "\\include{macros}"])
def test_input_forms_followed_for_definitions(tmp_path, inp):
    from scitexlintr._macros import defined_macros_in_file

    (tmp_path / "macros.tex").write_text(r"\newcommand{\LocalVal}{3}" + "\n")
    main = tmp_path / "main.tex"
    main.write_text(inp + "\n\\begin{document}\\end{document}\n")
    assert "LocalVal" in defined_macros_in_file(main)


# -------------------- codex review round 2 --------------------


def test_display_text_whitespace_is_meaningful():
    m = parse_manifest({"numbers": [{"id": "sig", "value": "x", "display": "not significant"},
                                    {"id": "ci", "value": 0.95, "display": r"95\% CI"}]})
    assert "snapshot-mismatch" in rules_of(r"\SciVal{\SIG}{notsignificant} a.", manifest=m)
    assert "snapshot-mismatch" in rules_of(r"\SciVal{\CI}{95\%CI} a.", manifest=m)
    assert "snapshot-mismatch" not in rules_of(r"\SciVal{\CI}{95\%  CI} a.", manifest=m)


@pytest.mark.parametrize("lit", [r"97\%", r"97.0\%", r"97.00\%"])
def test_rendered_percent_trailing_zero_variants_are_errors(lit):
    m = parse_manifest({"numbers": [
        {"id": "n_pairs", "value": 97},
        {"id": "frac", "value": 0.97, "unit": "percent", "precision": 1},
    ]})
    found = [f for f in lint(rf"Coverage was {lit} of claims.", manifest=m) if f.rule == "raw-generated-value"]
    assert [(f.severity, "id=frac" in f.message) for f in found] == [("error", True)]


@pytest.mark.parametrize("end", ["% ANALYSIS_OK_END[]", "% ANALYSIS_OK_END[a,]", "% ANALYSIS_OK_END[a"])
def test_malformed_named_end_does_not_close_region(end):
    assert find_waivers(f"% ANALYSIS_OK_BEGIN[a]: why\nx\n{end}\n") == []


@pytest.mark.parametrize("lit", [r"96.5\,\%", r"96.5~\%", r"96.5\thinspace\%"])
def test_spaced_rendered_percent_not_also_unsourced(lit):
    rules = rules_of(rf"Dated {lit} of claims.")
    assert "raw-generated-value" in rules
    assert "unsourced-numeric-token" not in rules


def test_spaced_typographic_percent_not_unsourced():
    assert "unsourced-numeric-token" not in rules_of(r"About 50\,\% of claims.", manifest=None)
