"""Regressions from the third pre-release review."""

from __future__ import annotations

import hashlib

import pytest

from scitexlintr import lint_html, parse_manifest

SRC = "a" * 64


def page(body: str) -> str:
    return "<!doctype html><html><head><title>t</title></head><body>\n" + body + "\n</body></html>"


def rules(fs):
    return sorted(f.rule for f in fs)


def h(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


M = parse_manifest({
    "numbers": [{"id": "frac", "value": 0.95, "unit": "percent", "precision": 1}],
    "figures": [{"id": "fig", "path": "f.svg", "sha256": SRC}],
    "data": [{"id": "d", "path": "d.json", "sha256": SRC}, {"id": "t", "path": "t.csv", "sha256": SRC}],
})


def lint(body):
    return lint_html(page(body), manifest=M)


def fig(extra_inside: str = "", media: str = "<svg></svg>") -> str:
    return (f'<figure data-sci-fig="fig" data-sha256="{SRC}" data-content-sha256="{h(media)}">'
            f'<div class="sci-media"><!-- sci-media -->{media}<!-- /sci-media --></div>{extra_inside}'
            "<figcaption>Cap.</figcaption></figure>")


# -- the exemption covers exactly the fingerprinted region --------------------

def test_text_inside_a_registered_figure_but_outside_its_media_is_prose():
    assert rules(lint(fig("<p>Fitted EC50 was 3.71 uM.</p>"))) == ["unsourced-numeric-token"]


def test_image_inside_a_registered_figure_but_outside_its_media_is_unregistered():
    assert rules(lint(fig('<img alt="" src="data:image/png;base64,AA==">'))) == ["unfingerprinted-figure"]
    assert lint(fig(media='<img alt="" src="data:image/png;base64,AA==">')) == []


def test_hand_typed_rows_outside_a_registered_tables_generated_rows_are_prose():
    rows = "<tr><td>17</td></tr>"
    body = (f'<table data-sci-table="t" data-sha256="{SRC}" data-content-sha256="{h(rows)}">'
            f"<tbody><!-- sci-rows -->{rows}<!-- /sci-rows --></tbody>"
            "<tfoot><tr><td>Mean</td><td>29.4</td></tr></tfoot></table>")
    assert rules(lint(body)) == ["unsourced-numeric-token"]


# -- the gate enforces the runtime's selectors ----------------------------------

def test_data_block_must_be_application_json():
    payload = '{"x":[1]}'
    body = (f'<figure data-sci-interactive="ts"><script data-sci-data="d" data-sha256="{SRC}" '
            f'data-content-sha256="{h(payload)}">{payload}</script></figure>')
    found = lint(body)
    assert rules(found) == ["unfingerprinted-data"]
    assert "application/json" in found[0].message


def test_unregistered_non_javascript_script_is_unregistered_data():
    found = lint('<script type="application/json" id="x">[1,2,3,4,5,6,7,8]</script>')
    assert rules(found) == ["unfingerprinted-data"]
    assert lint('<script type="text/plain" id="note"></script>') == []  # empty: nothing to hide


# -- every embedding element is gated ----------------------------------------------

@pytest.mark.parametrize("snippet", [
    '<div><svg><image href="plot.png"/></svg></div>',
    '<picture><source srcset="a.png"><img alt="" src="data:image/png;base64,AA=="></picture>',
    '<video src="v.mp4"></video>',
    '<iframe src="x.html"></iframe>',
    '<canvas id="c"></canvas>',
    '<div><svg><image href="data:image/png;base64,AA=="/></svg></div>',
])
def test_embedding_elements_outside_registered_media_are_flagged(snippet):
    assert "unfingerprinted-figure" in rules(lint(snippet)), snippet


def test_canvas_inside_an_interactive_figure_is_allowed():
    payload = '{"x":[1]}'
    body = (f'<figure data-sci-interactive="custom"><canvas></canvas>'
            f'<script type="application/json" data-sci-data="d" data-sha256="{SRC}" '
            f'data-content-sha256="{h(payload)}">{payload}</script></figure>')
    assert lint(body) == []


# -- integer attributes are ASCII integers --------------------------------------

def test_unicode_digit_precision_is_a_finding_not_a_crash():
    found = lint('<p><span data-sci-val="frac" data-precision="²">95%</span></p>')
    assert rules(found) == ["snapshot-mismatch"]
    assert "data-precision" in found[0].message


def test_unicode_digits_in_manifest_ids_do_not_crash_the_macro_transform():
    from scitexlintr._manifest import id_to_macro_name
    assert id_to_macro_name("r2_score") == "RTwoScore"
    # Only ASCII digits are spelled out; another digit character is kept, so
    # the key stays unique (HTML needs no TeX macro) instead of raising KeyError.
    assert id_to_macro_name("r²_score") == "R²Score"
    m = parse_manifest({"numbers": [{"id": "r²_score", "value": 0.91}]})
    assert lint_html(page('<p><span data-sci-val="r²_score">0.91</span></p>'), manifest=m) == []
