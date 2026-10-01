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
