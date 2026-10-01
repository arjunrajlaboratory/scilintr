"""Regressions from the second pre-release review."""

from __future__ import annotations

from scitexlintr import apply_fixes, lint_html, parse_manifest


def page(body: str) -> str:
    return "<!doctype html><html><head><title>t</title></head><body>\n" + body + "\n</body></html>"


def rules(fs):
    return sorted(f.rule for f in fs)


# -- display strings: HTML is HTML, TeX is TeX ---------------------------------

M = parse_manifest({"numbers": [
    {"id": "fold", "value": 3, "display_html": "3&times;"},
    {"id": "tiny", "value": 1e-4, "display_html": "1.0 × 10<sup>-4</sup>"},
    {"id": "ci", "value": 1.2, "display": "1.2--3.4"},
    {"id": "quote", "value": "alpha phrase", "display": "``alpha phrase''"},
]})


def test_display_html_is_markup_compared_by_rendered_text():
    assert lint_html(page('<p><span data-sci-val="fold">3&times;</span></p>'), manifest=M) == []
    assert lint_html(page('<p><span data-sci-val="fold">3×</span></p>'), manifest=M) == []
    assert lint_html(page('<p><span data-sci-val="tiny">1.0 × 10<sup>-4</sup></span></p>'), manifest=M) == []


def test_write_inserts_display_html_verbatim_even_over_markup():
    src = page('<p><span data-sci-val="tiny">1.0 × 10<sup>-5</sup></span> and <span data-sci-val="fold">2</span></p>')
    new, n = apply_fixes(src, lint_html(src, manifest=M), fmt="html")
    assert n == 2
    assert '<span data-sci-val="tiny">1.0 × 10<sup>-4</sup></span>' in new
    assert '<span data-sci-val="fold">3&times;</span>' in new
    assert lint_html(new, manifest=M) == []


def test_tex_ligatures_mark_a_display_as_tex():
    found = lint_html(page('<p><span data-sci-val="ci">1.2–3.4</span> <span data-sci-text="quote">“alpha phrase”</span></p>'), manifest=M)
    assert rules(found) == ["snapshot-mismatch", "snapshot-mismatch"]
    assert all("display_html" in f.message for f in found)


# -- rounded decimals are not evidence of a manifest value ----------------------

def test_decimal_renderings_do_not_claim_unrelated_literals():
    m = parse_manifest({"numbers": [
        {"id": "fold", "value": 1.4973, "unit": "decimal", "precision": 1},
        {"id": "eff", "value": 0.0512, "unit": "decimal", "precision": 2},
    ]})
    found = lint_html(page("<p>We added 1.5 mL of buffer.</p>"), manifest=m)
    assert rules(found) == ["unsourced-numeric-token"]


# -- script data literals ------------------------------------------------------

def script(js: str, attrs: str = "") -> str:
    return f"<script{attrs}>\n{js}\n</script>"


def test_script_data_literal_catches_common_shapes():
    for js in (
        "const d = [\n  0.1,\n  0.2,\n  0.35,\n  0.5,\n  0.8,\n  1.3,\n];",
        "const pts = [[0, 1.2], [1, 2.3], [2, 3.1]];",
        "const pts = [{x: 0, y: 1.2}, {x: 1, y: 2.3}, {x: 2, y: 3.1}];",
    ):
        assert rules(lint_html(page(script(js)))) == ["script-data-literal"], js


def test_script_data_literal_ignores_strings_comments_and_short_arrays():
    js = ("const margin = [12, 16, 38, 56];\n"
          "// [1, 2, 3, 4, 5, 6, 7] in a comment\n"
          "const label = '[1, 2, 3, 4, 5, 6, 7]';")
    assert lint_html(page(script(js))) == []


def test_only_the_first_runtime_block_is_exempt():
    runtime = script("var steps = [1, 2, 5, 10, 20, 50];", ' id="sci-report-runtime"')
    assert lint_html(page(runtime)) == []
    assert rules(lint_html(page(runtime + runtime))) == ["script-data-literal"]


def test_js_comment_waiver_inside_a_script():
    js = ("function f() {\n  const a = 1;\n  const b = 2;\n  const c = 3;\n  const d = 4;\n"
          "  // ANALYSIS_OK[script-data-literal]: fixed colour-stop offsets, not data\n"
          "  const stops = [0, 0.2, 0.4, 0.6, 0.8, 1];\n}")
    assert lint_html(page(script(js))) == []
    unrelated = js.replace("script-data-literal", "raw-generated-value")
    assert rules(lint_html(page(script(unrelated)))) == ["script-data-literal"]


def test_string_values_match_whole_words_only():
    m = parse_manifest({"numbers": [{"id": "grp", "value": "WT"}]})
    assert lint_html(page("<p>The WTF1 locus and SWT cells.</p>"), manifest=m) == []
    assert rules(lint_html(page("<p>Only WT cells grew.</p>"), manifest=m)) == ["raw-generated-value"]
    from scitexlintr import lint_tex
    assert lint_tex("The WTF1 locus.", manifest=m) == []
    assert rules(lint_tex("Only WT cells grew.", manifest=m)) == ["raw-generated-value"]


def test_index_expressions_and_call_arguments_are_not_data():
    # From a real report's custom figure: indexes and method arguments inside
    # an array literal are code, not data.
    js = ("var parts = [[cols[0], (+t[i]).toFixed(1)], [names[0] || cols[1], fmt(lo[i])],"
          " [names[1] || cols[2], fmt(hi[i])], [names[2] || cols[3], fmt(df[i])]];")
    assert lint_html(page(script(js))) == []
    assert rules(lint_html(page(script("var d = [[0, 1.2], [1, 2.3], [2, 3.1]];")))) == ["script-data-literal"]
