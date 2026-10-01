"""Regressions from the fourth end-to-end run (entropy-development synthesis)."""

from __future__ import annotations

import hashlib
import json

from scitexlintr import lint_html, lint_tex, parse_manifest
from scitexlintr._manifest import worked_rows_sha256


def page(body: str) -> str:
    return "<!doctype html><html><head><title>t</title></head><body>\n" + body + "\n</body></html>"


def rules(fs):
    return sorted(f.rule for f in fs)


TERMS = parse_manifest({"terms": [
    {"id": "occupancy_width", "expansion": "occupancy width",
     "overloaded_warning": "This is not the Gaussian width."},
    {"id": "PEC", "expansion": "perturbational equivalence class", "match": ["equivalence class"],
     "overloaded_warning": "Not an equivalence class in the algebraic sense."},
]})


def test_overloaded_terms_match_their_expansion_and_match_list():
    assert rules(lint_html(page("<p>The occupancy width grew.</p>"), manifest=TERMS)) == ["overloaded-term-no-warning"]
    assert rules(lint_html(page("<p>Each equivalence class held two states.</p>"), manifest=TERMS)) == ["overloaded-term-no-warning"]
    ok = "<p>This is not the Gaussian width. The occupancy width grew.</p>"
    assert lint_html(page(ok), manifest=TERMS) == []
    same_sentence = "<p>The occupancy width (This is not the Gaussian width.) grew.</p>"
    assert lint_html(page(same_sentence), manifest=TERMS) == []
    assert rules(lint_tex("The occupancy width grew.", manifest=TERMS)) == ["overloaded-term-no-warning"]


def test_slug_ids_are_not_required_in_prose():
    # The id alone (a slug) is still matched when it does appear.
    assert rules(lint_html(page("<p>occupancy_width rose.</p>"), manifest=TERMS)) == ["overloaded-term-no-warning"]


ROWS = [{"snp_id": "X17", "N": 5, "Y": 3, "alt_fraction": 0.6}, {"snp_id": "X2", "N": 2, "Y": 1, "alt_fraction": 0.5}]
WORKED = parse_manifest({
    "numbers": [{"id": "n_seed", "value": 5}],
    "worked_examples": [{"id": "c017", "subject_id": "c_017", "rows": ROWS}],
})


def worked_table(rows_html: str, sha: str | None = None, csha: str | None = None, wid: str = "c017") -> str:
    sha = worked_rows_sha256(ROWS) if sha is None else sha
    csha = hashlib.sha256(rows_html.encode()).hexdigest() if csha is None else csha
    return (f'<table class="sci-table" data-sci-worked="{wid}" data-sha256="{sha}" data-content-sha256="{csha}">'
            "<caption>Worked example for cell c_017.</caption>"
            f"<tbody><!-- sci-rows -->{rows_html}<!-- /sci-rows --></tbody></table>")


ROWS_HTML = "<tr><td>X17</td><td>5</td><td>3</td><td>0.6</td></tr><tr><td>X2</td><td>2</td><td>1</td><td>0.5</td></tr>"


def test_registered_worked_example_rows_are_fingerprinted_not_prose():
    # The cells include 5 (a registered value): no raw-generated-value inside the rows.
    assert lint_html(page(worked_table(ROWS_HTML)), manifest=WORKED) == []


def test_worked_example_table_detects_stale_rows_edits_and_unknown_ids():
    stale = worked_table(ROWS_HTML, sha="0" * 64)
    assert rules(lint_html(page(stale), manifest=WORKED)) == ["unfingerprinted-data"]
    edited = worked_table(ROWS_HTML).replace("<td>0.6</td>", "<td>0.7</td>")
    assert rules(lint_html(page(edited), manifest=WORKED)) == ["unfingerprinted-data"]
    assert rules(lint_html(page(worked_table(ROWS_HTML, wid="nope")), manifest=WORKED)) == ["unfingerprinted-data"]


def test_worked_rows_hash_is_canonical_json():
    expected = hashlib.sha256(json.dumps(ROWS, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    assert worked_rows_sha256(ROWS) == expected
    assert worked_rows_sha256(list(reversed(ROWS))) != expected  # row order is content
