# scilintr

Static analysis for R scientific data analysis code.

Flags patterns that often correspond to hidden scientific commitments:

- silent `tryCatch` error swallowing
- smuggled function-signature defaults
- label leakage in selection-stage code
- magic-eps floors in BIC / log formulas
- shadow-overwrite of sourced helpers
- ... and 35 other rules.

Designed for agentic coding workflows: **high recall over precision**,
structured `ANALYSIS_OK[category]:` waivers as the audit trail. Many
findings will be legitimate exceptions; an LLM agent (or its reviewer)
reads each finding and either fixes it or adds a waiver. The cost of
"look at this and decide" is near zero for an agent, so the linter can
be aggressive about flagging.

See [`../../analysis_lint_strategy.md`](../../analysis_lint_strategy.md)
for the rule definitions and design rationale, and
[`../../docs/failure-modes.md`](../../docs/failure-modes.md) for the
catalogue of bugs each rule catches.

## Status

v0.0.0.9000 — fixture-driven TDD scaffold. Rules R001–R040 have test
fixtures; rule implementations are stubs that will be filled in one
rule at a time, fixture-by-fixture.

## Usage

```r
remotes::install_github("user/scilintr")

# in a project root:
scilintr::lint_project(".")
```

CLI:

```bash
Rscript -e 'scilintr::main()' path/to/project
```

## Development

```r
devtools::test()                 # run all fixture tests
devtools::test_active_file()     # iterate on one rule
```

Test fixtures live in `tests/testthat/fixtures/R<NN>_<slug>/`. The
contract is encoded in the fixture file itself: a
`# EXPECTED: R<NN> at line <N>` header tells the test driver what
finding the rule should produce. Good fixtures have no EXPECTED
header.

Cross-file rules use subdirectory fixtures (`bad_<case>/` containing
multiple `.R` files) so the test driver lints the directory as a
project.
