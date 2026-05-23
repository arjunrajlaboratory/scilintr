# scilintr

Scientific code lint for R and Python analysis projects.

Flags patterns that often correspond to hidden scientific commitments:

- silent error swallowing (`tryCatch(..., error = function(e) NA)`)
- smuggled function-signature defaults (`top_modules = 25L`)
- label leakage in selection-stage code
- magic-eps floors in log/BIC formulas
- shadow-overwrite of sourced helpers
- "best of either side" reporting against a label
- silent absence propagation (`if (!file.exists(p)) return(NULL)`)
- ...and 37 other rules.

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
├── r/scilintr/                 <- R package (v0.1.0, 44 rules, 155 tests)
│   └── ...
└── py/scilintr/                <- Python package (v0.1.0, 27 rules, 139 tests)
    └── ...
```

Both packages implement the same rule spec from `analysis_lint_strategy.md`
and share the structured-waiver mechanism, the `Finding` record schema,
and the CLI surface. They are deliberately not 1:1: the R package has
more rules because most of the leakage-driven failure modes (R029
read.csv mangling, R030 silent tryCatch, R-specific shadow-overwrite
and scriptwise cross-file drift) come from R-style research codebases.
The Python package covers the universal scientific-code failure modes
plus a few Python-specific ones (`runtime-assert`, `unconsumed-cli-flag`,
`unvalidated-config`, `sentinel-mask-assignment`). See the
"Implementation status" section of
[`analysis_lint_strategy.md`](analysis_lint_strategy.md) for the full
rule-code cross-reference table.

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
pip install "scilintr @ git+https://github.com/arjunrajlaboratory/scilintr.git#subdirectory=py/scilintr"
```

CLI:

```bash
scilintr path/to/analysis/                       # lint a file or directory
scilintr --rules broad-exception path/to/file.py # restrict to a rule
scilintr --summary path/to/dir/                  # per-rule counts only
scilintr --no-waivers path/to/file.py            # audit mode
```

Library:

```python
from scilintr import lint_code, lint_paths, Finding
findings = lint_code(source_string, filename="foo.py")
findings = lint_paths(["path/to/dir/"])
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

- **R package (v0.1.0)** — 44 rules implemented (R001–R044, including
  R020/R025/R026 cross-file). 155 testthat fixtures passing. `R CMD
  check --as-cran` clean. Tested against real analysis code with a
  ~62% noise reduction from naive matching (after v1.1 tightening).
- **Python package (v0.1.0)** — 27 rules implemented (`broad-exception`,
  `unchecked-merge`, `magic-threshold`, `label-in-blind-stage`,
  `synthetic-data-generation`, …). 139 pytest tests passing. `python -m
  build` produces clean wheel + sdist; `twine check` PASSED.

Neither is on PyPI / CRAN yet — install from this repo via the
commands above. Both are structurally ready for upload when the time
comes.

## See also

- [`analysis_lint_strategy.md`](analysis_lint_strategy.md) — the canonical
  rule spec and design rationale.
- [`docs/failure-modes.md`](docs/failure-modes.md) — catalogued analysis
  and code failure modes that motivate each rule.
- [`r/scilintr/README.md`](r/scilintr/README.md) — R package details.
- [`py/scilintr/README.md`](py/scilintr/README.md) — Python package details.

## License

MIT.
