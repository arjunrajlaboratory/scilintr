# scilintr

Static analysis for R scientific data analysis code. Sibling of
[`py/scilintr/`](../../py/scilintr/) (Python code) and
[`tex/scitexlintr/`](../../tex/scitexlintr/) (LaTeX reports); same
agent-first design (high recall, structured `ANALYSIS_OK[category]:`
waivers).

Flags patterns that often correspond to hidden scientific commitments:

- silent `tryCatch` error swallowing
- `if (!file.exists(path)) return(NULL)` silent absence propagation
- smuggled function-signature defaults
- label leakage in selection-stage code
- magic-eps floors in BIC / log formulas
- shadow-overwrite of sourced helpers
- optparse flags declared but never read
- ... and 37 other rules (R001–R044).

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

v0.1.0 — all 40+ rules implemented (R001–R044, with R020/R025/R026
cross-file). 155 fixture tests passing. Rules R041–R044 were ported
back from the Python sibling (`py/scilintr/`) — they catch failure
modes (silent absence propagation, unconsumed CLI flags, unvalidated
config, empty-string sentinel masks) that the Python package
encountered first in real code.

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
