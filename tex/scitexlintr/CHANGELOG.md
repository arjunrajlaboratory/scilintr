# Changelog — scitexlintr

## [0.2.0] - Unreleased

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
- HTML port of the end-to-end corpus (`tests/data/report.html`).
- CI workflow for this package (`.github/workflows/tex-check.yaml`).

### Changed

- Threshold rules also recognize Unicode `≤ ≥ ≪ ≫` in TeX and HTML prose.
- `raw-generated-value` suggests `\SciText` (not `\SciVal`) for string
  values.
- `apply_fixes` takes `fmt="tex" | "html"` (default `"tex"`, unchanged).

## [0.1.0]

Initial release: 10 rules for LaTeX reports.
