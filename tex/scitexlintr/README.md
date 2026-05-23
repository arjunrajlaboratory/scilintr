# scitexlintr

Scientific lint for LaTeX reports — catches numeric drift, raw generated
values, unfingerprinted figures, and unsourced claims in `.tex` source.

This is a working v0.1 implementation of the package described in
`scitexlintr_readme_sketch.md` (in the scilintr repo root, not yet
published). The full README is to be lifted from that sketch once the
package stabilises.

## Quickstart

```bash
pip install -e ".[dev]"
scitexlintr tests/data/report.tex --manifest=tests/data/manifest.json
```

Use `--write` to auto-fix `snapshot-mismatch` findings, `--summary` for a
per-rule count, and `--no-waivers` to audit through `% ANALYSIS_OK[...]`
suppressions.

## Rules

See the source in `src/scitexlintr/_rules/` — one file per rule:

- `snapshot-mismatch` (error, auto-fixable)
- `raw-generated-value` (error)
- `bare-generated-macro` (warning)
- `unwrapped-threshold` (error)
- `unfingerprinted-figure` (error)
- `unsourced-numeric-token` (warning)
- `overloaded-term-no-warning` (warning)
- `forbidden-alias` (error)
- `handwritten-numeric-claim` (warning, manifest-free)
- `magic-tex-threshold` (warning, manifest-free)

## Tests

```bash
pytest
```

The end-to-end corpus is `tests/data/report.tex` + `tests/data/manifest.json`.
Each marker comment `% LINT-EXPECT[rule]` or `% LINT-OK` on the line
immediately above a code line documents (and asserts) what the linter
should find on that line.
