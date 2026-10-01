# Changelog — scitexlintr

## [0.2.0] - 2026-10-01

### Added

- **HTML report frontend.** `.html` / `.htm` files are linted with the same
  rule catalog and manifest contract as `.tex` (`lint_html`, and `lint_file`
  / the CLI choose the frontend by extension). Value wrappers are
  `<span data-sci-val="id">…</span>` / `data-sci-text`, whose rendered text
  is checked against the manifest and rewritten by `--write`. Waivers are
  `<!-- ANALYSIS_OK[rule]: … -->` comments.
- Display contract (`unit`, `precision`, `display`, `display_html`) is now
  read from the manifest and applied when checking HTML rendered values.
- `unknown-value-id` (HTML, error): a wrapper naming no manifest id.
- `unfingerprinted-data` (HTML, error): interactive-figure data blocks must
  be registered in the new optional `data[*]` manifest key with a matching
  sha256.
- `unfingerprinted-figure` (HTML): every `<figure>` must declare
  `data-sci-fig` (checked against `figures[*]` and its sha256),
  `data-sci-interactive`, or `data-sci-diagram`.
- Content hashes: inlined figure media and data payloads carry
  `data-content-sha256`, recomputed by the linter, so hand edits to inlined
  content fail the gate.
- Registered tables (`<table data-sci-table="id">`): rows generated from a
  `data[*]` file are fingerprinted and excluded from prose.
- `script-data-literal` (HTML, warning): numeric arrays typed into report
  scripts.
- `unit: "decimal"` with `precision`; half-up rounding for derived values;
  per-span `data-precision`; plain-text `display` accepted in HTML.
- `raw-generated-value` also flags the rendered form of a unit-derived value
  (`95.4%`, `95.4\%`).
- `<time>` content is not prose.
- `--version`; the CLI reports a missing input file instead of a traceback.
- HTML value spans resolve by exact id, or by a namespace-free key only
  when exactly one entry maps to it; a wrong or ambiguous namespace is
  `unknown-value-id` rather than a silent match to another analysis.
- A registered HTML figure must carry its media between `sci-media`
  markers with a content hash; `data-sha256` alone is not enough.
- Derived values with non-finite or very large magnitudes are reported as
  findings instead of aborting the run.
- `display_html` is HTML markup: compared by rendered text, inserted
  verbatim by `--write`. TeX ligatures (`--`, quotes) mark a `display` as TeX.
- Only fractional percents are attributed to a manifest value from their
  rendered form; rounded decimals fall to `unsourced-numeric-token`.
- String values match on word boundaries in TeX and HTML (`WT` is not raw
  inside `WTF1`).
- `script-data-literal` scans balanced brackets with strings and comments
  removed, exempts only the first runtime block, and honours
  `// ANALYSIS_OK[…]` waivers inside scripts.
- The prose exemption and "registered media" status cover exactly the
  hashed region between `sci-media` / `sci-rows` markers, not the whole
  `<figure>` / `<table>`.
- Data blocks must be `type="application/json"`, matching the runtime; other
  non-JavaScript scripts with content are unregistered data.
- Every media-embedding element is gated, not only `<img>` / `<object>` /
  `<embed>`.
- `data-precision` and the id→macro transform accept ASCII digits only
  (a `²` no longer crashes the run).
- `--fail-on=error` exits 1 only for error-severity findings (default
  `any` is unchanged).
- In TeX, the fix suggested for a rendered-form `raw-generated-value` uses
  the stored value as the `\SciVal` snapshot, which is what TeX checks.
- `overloaded-term-no-warning` recognizes a term by its `expansion` and an
  optional `match` list as well as its `id` (slug ids rarely appear in
  prose). Existing TeX reports may see new warnings from this rule; they
  are warnings, not errors.
- Worked-example tables (`data-sci-worked`) are fingerprinted against
  `manifest.worked_examples[*].rows`.
- Phrase rules (string `raw-generated-value`, `forbidden-alias` and its
  canonical-label exemption, `overloaded-term-no-warning` spellings and
  warning text) match across any whitespace run — a line break in the
  source, inline HTML markup, `&nbsp;`, or a TeX `~` tie — through one shared
  `phrase_pattern`. Existing TeX reports whose forbidden aliases wrap across
  a source line will now see those `forbidden-alias` errors.
- `script-data-literal` treats a bracket after `return`, `yield`, `await`,
  `typeof`, `case`, `export default` (and similar keywords) as an array
  literal, not an index access.
- An HTML value span whose manifest entry has no value is an error (the
  span's text is excluded from prose, so it would otherwise vouch for any
  number); a character reference that encodes a digit counts as that digit.
- A root `<svg>` outside a registered region is unregistered media unless
  it is a declared diagram, an interactive figure's chart, or marked
  `data-sci-icon`; `data-sci-live` readouts are exempt only inside
  interactive figures; SVG `<title>` text is prose.
- Wrapper text keeps line breaks and block boundaries as separation
  (`12<br>34` is not `1234`); duplicate attributes are read first-wins, as
  a browser does.
- HTML port of the end-to-end corpus (`tests/data/report.html`).
- CI workflow for this package (`.github/workflows/tex-check.yaml`).

### Changed

- Threshold rules also recognize Unicode `≤ ≥ ≪ ≫` in TeX and HTML prose.
- `raw-generated-value` suggests `\SciText` (not `\SciVal`) for string
  values.
- `apply_fixes` takes `fmt="tex" | "html"` (default `"tex"`, unchanged).

## [0.1.0]

Initial release: 10 rules for LaTeX reports.
