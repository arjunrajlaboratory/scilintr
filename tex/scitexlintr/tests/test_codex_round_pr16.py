"""Codex review on PR #16: phrase matching across markup, keyword-led arrays."""

from __future__ import annotations

import pytest

from scitexlintr import lint_html, lint_tex, parse_manifest


def page(body: str) -> str:
    return "<!doctype html><html><head><title>t</title></head><body>\n" + body + "\n</body></html>"


def rules(fs):
    return sorted(f.rule for f in fs)


M = parse_manifest({
    "numbers": [
        {"id": "contrast", "value": "treated versus control"},
        {"id": "acc", "value": 0.97, "label_canonical": "exact match accuracy",
         "label_aliases_forbidden": ["total cells"]},
    ],
    "terms": [{"id": "OW", "expansion": "occupancy width", "overloaded_warning": "This is not the Gaussian width."}],
})


@pytest.mark.parametrize("prose", [
    "<p>For treated <em>versus</em> control we saw a shift.</p>",
    "<p>For treated\n   versus control we saw a shift.</p>",
    "<p>For treated&nbsp;versus control we saw a shift.</p>",
])
def test_string_values_match_across_markup_and_line_breaks(prose):
    assert "raw-generated-value" in rules(lint_html(page(prose), manifest=M))


def test_forbidden_alias_and_canonical_label_match_across_markup():
    assert "forbidden-alias" in rules(lint_html(page("<p>The <b>total</b> cells were counted.</p>"), manifest=M))


def test_overloaded_term_and_its_warning_match_across_markup():
    assert rules(lint_html(page("<p>The <em>occupancy</em> width grew.</p>"), manifest=M)) == ["overloaded-term-no-warning"]
    ok = "<p>This is <em>not</em> the Gaussian width. The occupancy width grew.</p>"
    assert lint_html(page(ok), manifest=M) == []


def test_tex_phrases_match_across_line_breaks_and_ties():
    assert "raw-generated-value" in rules(lint_tex("For treated\nversus control we saw a shift.", manifest=M))
    assert "raw-generated-value" in rules(lint_tex("For treated~versus control we saw a shift.", manifest=M))
    ok = "This is not the\nGaussian width. The occupancy width grew."
    assert lint_tex(ok, manifest=M) == []


def script(js: str) -> str:
    return f"<script>\n{js}\n</script>"


@pytest.mark.parametrize("js", [
    "function f() { return [1, 2, 3, 4, 5, 6]; }",
    "function* g() { yield [1, 2, 3, 4, 5, 6]; }",
    "async function h() { await [1, 2, 3, 4, 5, 6]; }",
    "switch (k) { case [1, 2, 3, 4, 5, 6]: break; }",
    "const t = typeof [1, 2, 3, 4, 5, 6];",
])
def test_keyword_led_arrays_are_literals_not_index_accesses(js):
    assert rules(lint_html(page(script(js)))) == ["script-data-literal"], js


def test_identifier_led_brackets_are_still_index_accesses():
    js = "var v = [cols[0], cols[1], cols[2], returns[3], x[4], y[5], z[6]];"
    assert lint_html(page(script(js))) == []


# -- Codex re-review on 9e5e37c --------------------------------------------------

def test_wrapper_backed_by_a_null_value_is_an_error():
    m = parse_manifest({"numbers": [{"id": "result", "value": None}, {"id": "missing"}]})
    found = lint_html(page('<p><span data-sci-val="result">99.9</span> and <span data-sci-val="missing">3</span></p>'), manifest=m)
    assert rules(found) == ["snapshot-mismatch", "snapshot-mismatch"]
    assert all("no value" in f.message for f in found)


def test_digits_written_as_character_references_are_prose_digits():
    assert "handwritten-numeric-claim" in rules(lint_html(page("<p>We saw n = &#49;&#50; cells.</p>")))
    assert lint_html(page("<p>A range&#8211;wide dash.</p>")) == []  # a non-digit reference adds no digits


def test_export_default_array_is_a_literal_but_a_property_index_is_not():
    assert rules(lint_html(page(script("export default [1, 2, 3, 4, 5, 6];")))) == ["script-data-literal"]
    js = "var v = [obj.default[0], obj.default[1], o.return[2], a[3], b[4], c[5]];"
    assert lint_html(page(script(js))) == []


# -- Codex re-review on 1f39026 ------------------------------------------------

def test_live_readouts_are_exempt_only_inside_interactive_figures():
    assert "unsourced-numeric-token" in rules(lint_html(page("<p>Result: <output data-sci-live>999</output></p>")))
    inside = ('<figure data-sci-interactive="ts"><output data-sci-live>999</output>'
              '<script type="application/json" data-sci-data="d">{}</script></figure>')
    assert "unsourced-numeric-token" not in rules(lint_html(page(inside)))


def test_a_bare_svg_plot_outside_a_figure_is_unregistered_media():
    m = parse_manifest({"numbers": []})
    found = lint_html(page('<div><svg viewBox="0 0 100 100"><path d="M0 0L100 100"/></svg></div>'), manifest=m)
    assert rules(found) == ["unfingerprinted-figure"]
    icon = '<button><svg data-sci-icon viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2v11l9-5z"/></svg>Present</button>'
    assert lint_html(page(icon), manifest=m) == []
    diagram = '<figure data-sci-diagram><svg viewBox="0 0 4 4"><text>Input</text></svg></figure>'
    assert lint_html(page(diagram), manifest=m) == []


# -- Codex re-review on 00b92e2 --------------------------------------------------

def test_aria_hidden_alone_does_not_exempt_a_plot_but_a_control_icon_is_exempt():
    m = parse_manifest({"numbers": []})
    plot = '<div><svg aria-hidden="true" viewBox="0 0 100 100"><path d="M0 0L100 100"/></svg></div>'
    assert rules(lint_html(page(plot), manifest=m)) == ["unfingerprinted-figure"]
    icon = '<a href="#x"><svg data-sci-icon viewBox="0 0 16 16"><path d="M4 2v11l9-5z"/></svg>Next</a>'
    assert lint_html(page(icon), manifest=m) == []


def test_svg_title_text_in_a_diagram_is_prose():
    body = "<figure data-sci-diagram><svg><title>Result 999</title><text>Input</text></svg></figure>"
    assert rules(lint_html(page(body))) == ["unsourced-numeric-token"]


# -- Codex re-review on daeb36a --------------------------------------------------

def test_only_explicitly_marked_icons_are_exempt():
    m = parse_manifest({"numbers": []})
    linked_plot = '<a href="#full"><svg viewBox="0 0 100 100"><path d="M0 0L100 100"/></svg></a>'
    assert rules(lint_html(page(linked_plot), manifest=m)) == ["unfingerprinted-figure"]
    icon = '<button><svg data-sci-icon viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2v11l9-5z"/></svg>Play</button>'
    assert lint_html(page(icon), manifest=m) == []


def test_line_breaks_inside_a_wrapper_separate_its_text():
    m = parse_manifest({"numbers": [{"id": "x", "value": 1234}]})
    assert rules(lint_html(page('<p><span data-sci-val="x">12<br>34</span></p>'), manifest=m)) == ["snapshot-mismatch"]
    assert lint_html(page('<p><span data-sci-val="x">1<b>2</b>34</span></p>'), manifest=m) == []


def test_duplicate_attributes_use_the_first_like_a_browser():
    m = parse_manifest({"numbers": [{"id": "a", "value": 1}, {"id": "b", "value": 2}]})
    assert rules(lint_html(page('<p><span data-sci-val="a" data-sci-val="b">2</span></p>'), manifest=m)) == ["snapshot-mismatch"]
