"""HTML frontend — the same rule catalog applied to ``.html`` report sources.

The HTML wrapper convention replaces ``\\SciVal{\\Macro}{snapshot}`` with a
span whose *rendered text* is the snapshot:

    <span data-sci-val="diff-expr.n_samples">48</span>
    <span data-sci-text="diff-expr.contrast_phrase">treated versus control</span>

HTML has no macro expansion, so the rendered text is itself checked against
the manifest (and rewritten by ``--write``). Figures, interactive data blocks,
and waivers each get an HTML spelling; see the README's HTML section.
"""

from __future__ import annotations

import pytest

from scitexlintr import apply_fixes, lint_file, lint_html, parse_manifest
from scitexlintr.cli import main as cli_main

SHA_VOLCANO = "a" * 64
SHA_SERIES = "b" * 64

MANIFEST_JSON = {
    "numbers": [
        {
            "id": "diff-expr.n_samples",
            "value": 48,
            "label_canonical": "number of cells passing QC",
            "label_aliases_forbidden": ["total cells"],
        },
        {"id": "diff-expr.n_de_genes", "value": 317},
        {"id": "diff-expr.fdr_threshold", "value": 0.05},
        {"id": "diff-expr.contrast_phrase", "value": "treated versus control"},
        {"id": "frac_dated", "value": 0.9653, "unit": "percent", "precision": 1},
        {"id": "fold_change", "value": 2.5, "display": "$2.5\\times$"},
        {"id": "fold_change_html", "value": 2.5, "display": "$2.5\\times$",
         "display_html": "2.5×"},
    ],
    "figures": [
        {"id": "volcano", "path": "figures/volcano_de.svg", "sha256": SHA_VOLCANO},
        {"id": "umap", "path": "figures/umap.png", "sha256": None},
    ],
    "data": [
        {"id": "series", "path": "outputs/series.json", "sha256": SHA_SERIES},
    ],
    "terms": [
        {
            "id": "BCLRT",
            "expansion": "branch-coherency log-likelihood ratio test",
            "overloaded_warning": "Not a Wilks-sense LRT.",
        },
    ],
}

HEAD = (
    "<!doctype html>\n<html><head><title>Report 2026</title>\n"
    "<style>.x { width: 48px; }</style>\n</head>\n<body>\n"
)
TAIL = "\n</body></html>\n"


def page(body: str) -> str:
    return HEAD + body + TAIL


@pytest.fixture
def html_manifest():
    return parse_manifest(MANIFEST_JSON)


@pytest.fixture
def hlint(html_manifest):
    def _lint(body: str, **kwargs):
        kwargs.setdefault("manifest", html_manifest)
        return lint_html(page(body), filename="report.html", **kwargs)

    return _lint


def rules_of(findings) -> list[str]:
    return [f.rule for f in findings]


# ---------------------------------------------------------------------------
# Prose mask
# ---------------------------------------------------------------------------


def test_head_style_script_and_attributes_are_not_prose(hlint):
    body = (
        '<p class="w-48" data-n="317">Plain prose.</p>\n'
        "<script>const n = 317; if (x < 0.01) {}</script>\n"
        "<!-- 317 in a comment -->\n"
        "<pre>n = 48</pre><code>p = 0.01</code>\n"
    )
    assert hlint(body) == []


def test_numbers_in_ordinary_text_are_prose(hlint):
    assert "unsourced-numeric-token" in rules_of(hlint("<p>We saw 999 cells.</p>"))


def test_numbers_split_by_tags_are_separate_tokens(hlint):
    # "3<sup>2</sup>" must not glue into "32"; neither is in the manifest.
    found = [f for f in hlint("<p>Area 3<sup>2</sup>.</p>") if f.rule == "unsourced-numeric-token"]
    assert len(found) == 2


def test_numeric_character_references_do_not_leak_digits(hlint):
    assert hlint("<p>Range&#8211;wide &nbsp; &#x2014; effects.</p>") == []


def test_entity_escaped_threshold_is_seen(hlint):
    assert "magic-tex-threshold" in rules_of(hlint("<p>We used p &lt; 0.01 here.</p>"))
    assert "unwrapped-threshold" in rules_of(hlint("<p>At FDR &lt; 0.05 we kept genes.</p>"))


def test_unicode_comparison_threshold_is_seen(hlint):
    assert "magic-tex-threshold" in rules_of(hlint("<p>We kept p ≤ 0.01 hits.</p>"))


def test_live_readouts_are_not_prose(hlint):
    body = '<figure data-sci-interactive="t"><output data-sci-live>999</output></figure>'
    assert "unsourced-numeric-token" not in rules_of(hlint(body))


# ---------------------------------------------------------------------------
# Wrapper spans
# ---------------------------------------------------------------------------


def test_correct_wrappers_pass(hlint):
    body = (
        '<p>We analyzed <span data-sci-val="diff-expr.n_samples">48</span> cells.\n'
        'For <span data-sci-text="diff-expr.contrast_phrase">treated versus control</span>,\n'
        '<span data-sci-val="n_de_genes">317</span> genes changed.</p>'
    )
    assert hlint(body) == []


def test_stale_rendered_value_is_snapshot_mismatch(hlint):
    found = hlint('<p>We analyzed <span data-sci-val="diff-expr.n_samples">47</span> cells.</p>')
    assert rules_of(found) == ["snapshot-mismatch"]
    assert found[0].severity == "error"


def test_percent_unit_rendering_is_derived_from_value(hlint):
    assert hlint('<p><span data-sci-val="frac_dated">96.5%</span> of claims.</p>') == []
    stale = hlint('<p><span data-sci-val="frac_dated">0.9653</span> of claims.</p>')
    assert rules_of(stale) == ["snapshot-mismatch"]
    assert "96.5%" in stale[0].message


def test_display_html_override_is_verbatim(hlint):
    assert hlint('<p>A <span data-sci-val="fold_change_html">2.5×</span> shift.</p>') == []
    assert rules_of(hlint('<p>A <span data-sci-val="fold_change_html">2.5x</span> shift.</p>')) == [
        "snapshot-mismatch"
    ]


def test_tex_only_display_override_is_flagged_not_silently_skipped(hlint):
    found = hlint('<p>A <span data-sci-val="fold_change">2.5</span> shift.</p>')
    assert rules_of(found) == ["snapshot-mismatch"]
    assert "display_html" in found[0].message


def test_unknown_wrapper_id_is_an_error(hlint):
    found = hlint('<p><span data-sci-val="n_smaples">48</span> cells.</p>')
    assert rules_of(found) == ["unknown-value-id"]
    assert found[0].severity == "error"


def test_unknown_wrapper_id_needs_manifest(html_manifest):
    src = page('<p><span data-sci-val="nope">48</span> cells.</p>')
    assert lint_html(src, manifest=None) == []


def test_raw_value_in_html_prose_suggests_span(hlint):
    found = hlint("<p>We analyzed 48 cells.</p>")
    assert rules_of(found) == ["raw-generated-value"]
    assert 'data-sci-val="diff-expr.n_samples"' in found[0].message


def test_bare_generated_macro_never_fires_on_html(hlint):
    assert "bare-generated-macro" not in rules_of(hlint("<p>Literal \\NSamples text.</p>"))


def test_forbidden_alias_and_overloaded_term(hlint):
    assert "forbidden-alias" in rules_of(hlint("<p>The total cells were counted.</p>"))
    assert "overloaded-term-no-warning" in rules_of(hlint("<p>We ran BCLRT on each.</p>"))
    assert hlint("<p>We ran BCLRT (Not a Wilks-sense LRT.) on each.</p>") == []


def test_write_rewrites_rendered_text(html_manifest):
    src = page(
        '<p><span data-sci-val="diff-expr.n_samples">47</span> and '
        '<span data-sci-val="frac_dated">0.97</span>.</p>'
    )
    new_src, n = apply_fixes(src, lint_html(src, manifest=html_manifest), fmt="html")
    assert n == 2
    assert '<span data-sci-val="diff-expr.n_samples">48</span>' in new_src
    assert '<span data-sci-val="frac_dated">96.5%</span>' in new_src
    assert lint_html(new_src, manifest=html_manifest) == []


def test_write_html_escapes_string_values():
    manifest = parse_manifest({"numbers": [{"id": "label", "value": "A & B <x>"}]})
    src = page('<p><span data-sci-text="label">old</span></p>')
    new_src, n = apply_fixes(src, lint_html(src, manifest=manifest), fmt="html")
    assert n == 1
    assert '<span data-sci-text="label">A &amp; B &lt;x&gt;</span>' in new_src
    assert lint_html(new_src, manifest=manifest) == []


def test_write_skips_wrapper_containing_markup(html_manifest):
    src = page('<p><span data-sci-val="diff-expr.n_samples"><b>47</b></span></p>')
    findings = lint_html(src, manifest=html_manifest)
    assert rules_of(findings) == ["snapshot-mismatch"]
    new_src, n = apply_fixes(src, findings, fmt="html")
    assert n == 0 and new_src == src


# ---------------------------------------------------------------------------
# Figures and data
# ---------------------------------------------------------------------------


def registered_figure(fig_id: str, sha: str | None, media: str, caption: str = "") -> str:
    """Figure markup as sync_html_report.py writes it: media between the
    sci-media markers, with data-content-sha256 over exactly that text."""
    import hashlib

    sha_attr = f' data-sha256="{sha}"' if sha is not None else ""
    content = hashlib.sha256(media.encode("utf-8")).hexdigest()
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return (
        f'<figure data-sci-fig="{fig_id}"{sha_attr} data-content-sha256="{content}">'
        f'<div class="sci-media"><!-- sci-media -->{media}<!-- /sci-media --></div>{cap}</figure>'
    )


def test_registered_figure_with_matching_sha_passes(hlint):
    body = registered_figure("volcano", SHA_VOLCANO, '<svg viewBox="0 0 10 10"><text>1234</text></svg>', "Volcano plot.")
    assert hlint(body) == []


def test_figure_media_text_is_not_prose_but_caption_is(hlint):
    body = registered_figure("volcano", SHA_VOLCANO, "<svg><text>1234</text></svg>", "Shows 999 genes.")
    assert rules_of(hlint(body)) == ["unsourced-numeric-token"]


def test_stale_inline_figure_sha_is_flagged(hlint):
    found = hlint(registered_figure("volcano", "c" * 64, "<svg></svg>"))
    assert rules_of(found) == ["unfingerprinted-figure"]
    assert "sha256" in found[0].message


def test_missing_sha_attribute_is_flagged_when_manifest_has_one(hlint):
    assert rules_of(hlint(registered_figure("volcano", None, "<svg></svg>"))) == ["unfingerprinted-figure"]


def test_manifest_without_sha_accepts_any_registered_media(hlint):
    assert hlint(registered_figure("umap", None, '<img alt="" src="data:image/png;base64,AA==">')) == []


def test_unknown_figure_id_is_flagged(hlint):
    assert set(rules_of(hlint('<figure data-sci-fig="nope"><svg></svg></figure>'))) == {"unfingerprinted-figure"}


def test_undeclared_figure_is_flagged(hlint):
    assert set(rules_of(hlint("<figure><svg></svg><figcaption>Plot.</figcaption></figure>"))) == {"unfingerprinted-figure"}


def test_diagram_figure_is_allowed_and_its_text_is_prose(hlint):
    assert hlint("<figure data-sci-diagram><svg><text>Input</text></svg></figure>") == []
    body = "<figure data-sci-diagram><svg><text>999 cells</text></svg></figure>"
    assert rules_of(hlint(body)) == ["unsourced-numeric-token"]


def test_stray_img_outside_registered_figure(hlint):
    assert rules_of(hlint('<p><img alt="" src="figures/other.png"></p>')) == ["unfingerprinted-figure"]
    assert hlint('<p><img alt="" src="./figures/umap.png"></p>') == []


def test_registered_data_block_passes_and_stale_one_fails(hlint):
    ok = (
        '<figure data-sci-interactive="ts">'
        f'<script type="application/json" data-sci-data="series" data-sha256="{SHA_SERIES}" '
        'data-content-sha256="fc08fb1a99d15a3459a5c2b84b50ba956ccf3e5569878beb187329de51a69ff8">'
        '{"x": [1, 2, 3]}</script></figure>'
    )
    assert hlint(ok) == []
    stale = ok.replace(SHA_SERIES, "d" * 64)
    assert rules_of(hlint(stale)) == ["unfingerprinted-data"]
    unknown = ok.replace('data-sci-data="series"', 'data-sci-data="other"')
    assert rules_of(hlint(unknown)) == ["unfingerprinted-data"]


def test_interactive_figure_needs_registered_data(hlint):
    body = '<figure data-sci-interactive="ts"><script>draw([1,2,3])</script></figure>'
    assert rules_of(hlint(body)) == ["unfingerprinted-data"]


# ---------------------------------------------------------------------------
# Waivers
# ---------------------------------------------------------------------------


def test_html_comment_waiver_suppresses_named_rule(hlint):
    body = (
        "<!-- ANALYSIS_OK[unsourced-numeric-token]: publication year of the cited atlas -->\n"
        "<p>The atlas from 2019 was used.</p>"
    )
    assert hlint(body) == []


def test_html_waiver_is_rule_scoped(hlint):
    body = (
        "<!-- ANALYSIS_OK[raw-generated-value]: wrong rule -->\n"
        "<p>The atlas from 2019 was used.</p>"
    )
    assert rules_of(hlint(body)) == ["unsourced-numeric-token"]


def test_tex_percent_is_not_a_waiver_in_html(hlint):
    body = "<p>% ANALYSIS_OK[unsourced-numeric-token]: not a comment in HTML\n2019 atlas.</p>"
    assert "unsourced-numeric-token" in rules_of(hlint(body))


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def test_lint_file_dispatches_on_extension(tmp_path):
    report = tmp_path / "report.html"
    report.write_text(page("<p>We saw 999 cells.</p>"), encoding="utf-8")
    assert rules_of(lint_file(report)) == ["unsourced-numeric-token"]


def test_cli_write_on_html(tmp_path, capsys):
    import json

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(MANIFEST_JSON), encoding="utf-8")
    report = tmp_path / "report.html"
    report.write_text(page('<p><span data-sci-val="n_samples">1</span> cells.</p>'), encoding="utf-8")
    rc = cli_main([str(report), f"--manifest={manifest_path}", "--write"])
    assert rc == 0
    assert '<span data-sci-val="n_samples">48</span>' in report.read_text(encoding="utf-8")


def test_lines_and_columns_point_into_original_source(hlint):
    found = hlint("<p>\n  We saw 999 cells.</p>")
    (f,) = found
    source_lines = page("<p>\n  We saw 999 cells.</p>").splitlines()
    assert source_lines[f.line - 1][f.col - 1 : f.col + 2] == "999"



def test_implicitly_closed_wrapper_is_still_checked(hlint):
    # The span is closed only by </p>; it must not silently escape the check.
    found = hlint('<p>We analyzed <span data-sci-val="diff-expr.n_samples">47 cells.</p>')
    assert "snapshot-mismatch" in rules_of(found)


def test_nested_markup_inside_wrapper_does_not_end_it_early(hlint):
    body = '<p><span data-sci-val="n_samples"><span class="num">48</span></span> cells.</p>'
    assert hlint(body) == []
    stale = '<p><span data-sci-val="n_samples"><span class="num">47</span></span> cells.</p>'
    assert rules_of(hlint(stale)) == ["snapshot-mismatch"]


def test_uppercase_markup_is_normalized(hlint):
    assert rules_of(hlint('<P>We saw <SPAN DATA-SCI-VAL="n_samples">47</SPAN> cells.</P>')) == [
        "snapshot-mismatch"
    ]
