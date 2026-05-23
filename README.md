# scilintr

Scientific code lint for R and Python analysis projects.

Flags patterns that often correspond to hidden scientific commitments:

- silent error swallowing (`tryCatch(..., error = function(e) NA)`)
- smuggled function-signature defaults (`top_modules = 25L`)
- label leakage in selection-stage code
- magic-eps floors in log/BIC formulas
- shadow-overwrite of sourced helpers
- "best of either side" reporting against a label
- ...and 35 other rules.

Designed for **agentic coding workflows**: high recall over precision,
structured `ANALYSIS_OK[category]:` waivers as the audit trail. Many
findings will be legitimate; an LLM agent (or its reviewer) reads each
finding and either fixes the pattern or adds a structured waiver.

## What's in this monorepo

```
scilintr/
├── analysis_lint_strategy.md   <- the rule spec; language-agnostic
├── docs/
│   └── failure-modes.md        <- catalogued bugs each rule catches
├── r/scilintr/                 <- R package (working, 40 rules)
│   └── ...
└── py/scilintr/                <- Python package (scaffold; not yet implemented)
    └── ...
```

Both packages implement the same 40 rules against the same `analysis_lint_strategy.md`
spec, with the same structured-waiver mechanism. The rule IDs (R001–R040,
where the "R" stands for "Rule") are shared across languages.

## Install

### R

```r
# From GitHub:
remotes::install_github("arjunrajlaboratory/scilintr", subdir = "r/scilintr")

# In a project root:
scilintr::lint_project(".")
```

CLI:

```bash
Rscript -e 'scilintr::main()' path/to/project
```

### Python

```bash
# Scaffold only at this stage. Once implementation lands:
pip install "scilintr @ git+https://github.com/arjunrajlaboratory/scilintr.git#subdirectory=py/scilintr"
```

## Design point: agent-first

This linter is tuned for LLM-driven workflows where the cost of reading a
finding and deciding "fix or waive" is near zero. That changes the
cost-benefit math compared to a human-targeted linter:

- **High recall over precision.** Flag anything that *might* be a
  scientifically meaningful choice.
- **Structured waivers as audit trail.** Each accepted "false positive"
  becomes an `ANALYSIS_OK[category]: <reason>` comment — machine-grepable
  and human-readable.
- **Recall failures cost more than precision failures.** A missed bug
  ships; a flagged-but-fine line is a 10-second triage.

Humans can use it too — the waiver mechanism helps either way.

## How it works

For each `.R` (or `.py`) file in a project, scilintr walks the AST,
matches each rule's pattern (via `xml2`/XPath for R, `ast` for Python),
and emits a `Finding` record. The orchestrator then filters findings
covered by a nearby `ANALYSIS_OK[category]:` comment.

Cross-file rules (shadow-overwrite, definition drift, dead code) walk
every file once to build a project index, then run rules against the
index.

## Status

- **R package (v0.0.0.9000)** — 40 rules implemented, 131 fixture tests
  passing, tested against real analysis code with a ~62% noise reduction
  from naive matching (after v1.1 tightening).
- **Python package** — scaffold only. The rule spec, waiver mechanism,
  fixture taxonomy, and finding-record schema are designed for shared
  use; the Python implementation follows the same shape but is not yet
  written.

## See also

- [`analysis_lint_strategy.md`](analysis_lint_strategy.md) — the canonical
  rule spec and design rationale.
- [`docs/failure-modes.md`](docs/failure-modes.md) — catalogued analysis
  and code failure modes that motivate each rule.
- [`r/scilintr/README.md`](r/scilintr/README.md) — R package details.

## License

MIT.
