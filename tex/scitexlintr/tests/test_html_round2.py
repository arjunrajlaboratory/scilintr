"""Second-round HTML contract: content hashes, tables, dates, display, precision."""

from __future__ import annotations

import hashlib

import pytest

from scitexlintr import apply_fixes, lint_html, parse_manifest
from scitexlintr.cli import main as cli_main

SRC = "a" * 64


def h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def page(body: str) -> str:
    return "<!doctype html><html><head><title>t</title></head><body>\n" + body + "\n</body></html>"


M = parse_manifest({
    "numbers": [
        {"id": "n_cells", "value": 30},
        {"id": "frac", "value": 0.9535, "unit": "percent", "precision": 1},
        {"id": "mean_degree", "value": 7.47712, "unit": "decimal", "precision": 2},
        {"id": "plain_display", "value": 0.31831, "display": "0.3183"},
        {"id": "tex_display", "value": 3.2, "display": "3.2$\\times$"},
    ],
    "figures": [{"id": "fig", "path": "f.svg", "sha256": SRC}],
    "data": [{"id": "series", "path": "s.json", "sha256": SRC}, {"id": "tab", "path": "t.csv", "sha256": SRC}],
})


def lint(body, **kw):
    return lint_html(page(body), manifest=M, **kw)


def rules(fs):
    return [f.rule for f in fs]


# -- content hashes ----------------------------------------------------------

def data_block(payload: str, content_sha: str | None) -> str:
    csha = f' data-content-sha256="{content_sha}"' if content_sha is not None else ""
    return (f'<figure data-sci-interactive="ts"><script type="application/json" data-sci-data="series" '
            f'data-sha256="{SRC}"{csha}>{payload}</script></figure>')


def test_data_block_content_hash_detects_hand_edits():
    payload = '{"x":[1,2,3]}'
    assert lint(data_block(payload, h(payload))) == []
    edited = data_block('{"x":[1,2,4]}', h(payload))
    found = lint(edited)
    assert rules(found) == ["unfingerprinted-data"]
    assert "edited" in found[0].message


def test_data_block_without_content_hash_is_flagged():
    assert rules(lint(data_block('{"x":[1]}', None))) == ["unfingerprinted-data"]


def fig(media: str, content_sha: str | None) -> str:
    csha = f' data-content-sha256="{content_sha}"' if content_sha is not None else ""
    return (f'<figure data-sci-fig="fig" data-sha256="{SRC}"{csha}><div class="sci-media">'
            f"<!-- sci-media -->{media}<!-- /sci-media --></div><figcaption>Cap.</figcaption></figure>")


def test_figure_media_content_hash_detects_hand_edits():
    media = '<svg viewBox="0 0 1 1"><path d="M0 0L1 1"/></svg>'
    assert lint(fig(media, h(media))) == []
    assert rules(lint(fig(media.replace("L1 1", "L1 0"), h(media)))) == ["unfingerprinted-figure"]


def test_figure_content_hash_is_optional_without_markers():
    # A figure without sci-media markers (hand-inlined) keeps the 0.2.0 contract.
    body = f'<figure data-sci-fig="fig" data-sha256="{SRC}"><svg></svg></figure>'
    assert lint(body) == []


def test_numeric_array_literal_in_report_script_is_a_warning():
    found = lint("<script>draw([0.1, 0.2, 0.35, 0.5, 0.8, 1.3]);</script>")
    assert rules(found) == ["script-data-literal"]
    assert found[0].severity == "warning"
    assert lint("<script>const margin = [12, 16, 38, 56];</script>") == []
    runtime = '<script id="sci-report-runtime">var ticks = [1, 2, 5, 10, 20, 50];</script>'
    assert lint(runtime) == []


# -- registered tables -------------------------------------------------------

def test_registered_table_cells_are_not_prose_but_caption_is():
    rows = "<tr><td>17</td><td>0.42</td></tr><tr><td>18</td><td>0.91</td></tr>"
    body = (f'<table class="sci-table" data-sci-table="tab" data-sha256="{SRC}" data-content-sha256="{h(rows)}">'
            f"<caption>Per-seed results for 999 seeds.</caption><thead><tr><th>seed</th><th>score</th></tr></thead>"
            f"<tbody><!-- sci-rows -->{rows}<!-- /sci-rows --></tbody></table>")
    found = lint(body)
    assert rules(found) == ["unsourced-numeric-token"]  # the caption's 999, not the cells


def test_registered_table_needs_manifest_entry_and_fresh_hash():
    rows = "<tr><td>1</td></tr>"
    good = (f'<table data-sci-table="tab" data-sha256="{SRC}" data-content-sha256="{h(rows)}">'
            f"<tbody><!-- sci-rows -->{rows}<!-- /sci-rows --></tbody></table>")
    assert lint(good) == []
    assert rules(lint(good.replace('data-sci-table="tab"', 'data-sci-table="nope"'))) == ["unfingerprinted-data"]
    assert rules(lint(good.replace("<td>1</td>", "<td>2</td>"))) == ["unfingerprinted-data"]


# -- dates, display, precision ----------------------------------------------

def test_time_elements_are_not_prose():
    assert lint('<p class="byline"><time datetime="2026-09-30">30 September 2026</time></p>') == []


def test_plain_text_display_is_valid_html():
    assert lint('<p><span data-sci-val="plain_display">0.3183</span></p>') == []
    assert rules(lint('<p><span data-sci-val="tex_display">3.2</span></p>')) == ["snapshot-mismatch"]


def test_decimal_unit_and_half_up_rounding():
    assert lint('<p><span data-sci-val="mean_degree">7.48</span> links.</p>') == []
    # 0.9535 * 100 is 95.35 in decimal; half-up gives 95.4, not binary-float 95.3.
    assert lint('<p><span data-sci-val="frac">95.4%</span> of claims.</p>') == []


def test_per_span_precision_override():
    assert lint('<p><span data-sci-val="frac" data-precision="0">95%</span></p>') == []
    assert lint('<p><span data-sci-val="mean_degree" data-precision="1">7.5</span></p>') == []
    found = lint('<p><span data-sci-val="n_cells" data-precision="1">30.0</span></p>')
    assert rules(found) == ["snapshot-mismatch"]
    assert "data-precision" in found[0].message


def test_write_honors_per_span_precision():
    src = page('<p><span data-sci-val="frac" data-precision="0">90%</span></p>')
    new, n = apply_fixes(src, lint_html(src, manifest=M), fmt="html")
    assert n == 1 and '<span data-sci-val="frac" data-precision="0">95%</span>' in new


def test_rendered_form_of_derived_value_is_a_raw_value():
    assert rules(lint("<p>Of all claims, 95.4% were dated.</p>")) == ["raw-generated-value"]
    assert rules(lint("<p>The mean degree was 7.48 links.</p>")) == ["raw-generated-value"]


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli_main(["--version"])
    assert exc.value.code == 0
    assert "0.2.0" in capsys.readouterr().out


def test_cli_reports_missing_file_without_traceback(tmp_path, capsys):
    assert cli_main([str(tmp_path / "nope.html")]) == 2
    assert "not found" in capsys.readouterr().err
