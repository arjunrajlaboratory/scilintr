"""Regressions from the pre-release code review."""

from __future__ import annotations

import hashlib
import math

from scitexlintr import lint_html, lint_tex, parse_manifest
from scitexlintr._display import derive_unit

SRC = "a" * 64


def page(body: str) -> str:
    return "<!doctype html><html><head><title>t</title></head><body>\n" + body + "\n</body></html>"


def rules(fs):
    return sorted(f.rule for f in fs)


def test_bare_number_equal_to_a_percent_rendering_is_still_unsourced():
    m = parse_manifest({"numbers": [{"id": "frac", "value": 0.954, "unit": "percent", "precision": 1}]})
    assert rules(lint_html(page("<p>The protein weighs 95.4 kDa.</p>"), manifest=m)) == ["unsourced-numeric-token"]
    assert rules(lint_html(page("<p>Of all claims, 95.4% were dated.</p>"), manifest=m)) == ["raw-generated-value"]


def test_wrong_namespace_does_not_resolve_to_another_entry():
    m = parse_manifest({"numbers": [{"id": "a.n_samples", "value": 48}]})
    found = lint_html(page('<p><span data-sci-val="b.n_samples">48</span></p>'), manifest=m)
    assert rules(found) == ["unknown-value-id"]
    # A bare local key still resolves when it is unambiguous ...
    assert lint_html(page('<p><span data-sci-val="n_samples">48</span></p>'), manifest=m) == []


def test_ambiguous_local_key_is_unknown_not_silently_the_last_entry():
    m = parse_manifest({"numbers": [{"id": "a.n_samples", "value": 48}, {"id": "b.n_samples", "value": 96}]})
    assert rules(lint_html(page('<p><span data-sci-val="n_samples">96</span></p>'), manifest=m)) == ["unknown-value-id"]
    assert lint_html(page('<p><span data-sci-val="b.n_samples">96</span></p>'), manifest=m) == []


def test_registered_figure_without_media_markers_is_flagged():
    m = parse_manifest({"figures": [{"id": "x", "path": "x.png", "sha256": SRC}]})
    body = f'<figure data-sci-fig="x" data-sha256="{SRC}"><img alt="" src="data:image/png;base64,AA=="></figure>'
    found = lint_html(page(body), manifest=m)
    assert rules(found) == ["unfingerprinted-figure"]
    assert "sci-media" in found[0].message


def test_low_precision_derived_values_do_not_claim_every_integer():
    m = parse_manifest({"numbers": [
        {"id": "lanes", "value": 2.7, "unit": "decimal", "precision": 0},
        {"id": "ci", "value": 0.95, "unit": "percent", "precision": 0},
    ]})
    found = lint_html(page("<p>We ran 3 lanes with 95% confidence intervals.</p>"), manifest=m)
    assert "raw-generated-value" not in rules(found)
    assert "raw-generated-value" not in rules(lint_tex("We ran 3 lanes with 95\\% intervals.", manifest=m))


def test_non_finite_and_huge_values_are_reported_not_crashing():
    m = parse_manifest({"numbers": [
        {"id": "inf", "value": math.inf, "unit": "decimal", "precision": 2},
        {"id": "huge", "value": 10**30, "unit": "decimal", "precision": 2},
    ]})
    found = lint_html(page('<p><span data-sci-val="inf">x</span> <span data-sci-val="huge">y</span></p>'), manifest=m)
    assert rules(found) == ["snapshot-mismatch", "snapshot-mismatch"]
    assert "finite" in found[0].message
    assert derive_unit(10**30, "decimal", 2, percent_sign="") == "1000000000000000000000000000000.00"
