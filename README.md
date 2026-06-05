# scilintr

Scientific lint for R and Python analysis code, plus LaTeX scientific
reports.

Flags patterns that often correspond to hidden scientific commitments:

- silent error swallowing (`tryCatch(..., error = function(e) NA)`)
- smuggled function-signature defaults (`top_modules = 25L`)
- label leakage in selection-stage code
- magic-eps floors in log/BIC formulas
- shadow-overwrite of sourced helpers
- "best of either side" reporting against a label
- silent absence propagation (`if (!file.exists(p)) return(NULL)`)
- numeric drift between an analysis result and its written-up value in the
  report (a manifest-anchored check on the `.tex` source)
- ...and ~50 other rules across the three packages.

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
├── r/scilintr/                 <- R package (v0.1.1, 44 rules, 161 tests)
│   └── ...
├── py/scilintr/                <- Python package (v0.1.0, 27 rules, 139 tests)
│   └── ...
└── tex/scitexlintr/            <- LaTeX report linter (v0.1.0, 10 rules, 117 tests)
    └── ...
```

The R and Python packages implement the same analysis-code rule spec
from `analysis_lint_strategy.md` and share the structured-waiver
mechanism, the `Finding` record schema, and the CLI surface. They are
deliberately not 1:1: the R package has more rules because most of the
leakage-driven failure modes (R029 read.csv mangling, R030 silent
tryCatch, R-specific shadow-overwrite and scriptwise cross-file drift)
come from R-style research codebases. The Python package covers the
universal scientific-code failure modes plus a few Python-specific ones
(`runtime-assert`, `unconsumed-cli-flag`, `unvalidated-config`,
`sentinel-mask-assignment`). See the "Implementation status" section of
[`analysis_lint_strategy.md`](analysis_lint_strategy.md) for the full
rule-code cross-reference table.

The `tex/scitexlintr/` package is a sibling, not a port: it lints the
`.tex` source of scientific reports against a manifest of registered
values, figures, and terms. Its rule catalog (snapshot drift,
unfingerprinted figures, handwritten numeric claims, forbidden aliases,
…) is disjoint from the analysis-code rules — they catch drift between
the analysis and its writeup, not bugs inside the analysis. It uses the
same TeX-comment-flavored `% ANALYSIS_OK[rule]:` waiver convention. See
[`tex/scitexlintr/README.md`](tex/scitexlintr/README.md) for the full
catalog and the wrapper-macro / manifest contract.

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

### LaTeX reports (scitexlintr)

```bash
pip install "scitexlintr @ git+https://github.com/arjunrajlaboratory/scilintr.git#subdirectory=tex/scitexlintr"
```

CLI:

```bash
scitexlintr report.tex --manifest=.manifest.json   # lint a report
scitexlintr report.tex                              # manifest-free rules only
scitexlintr report.tex --manifest=... --write       # auto-fix snapshot drift
scitexlintr report.tex --no-waivers                 # audit mode
scitexlintr report.tex --rules=snapshot-mismatch    # restrict to specific rules
```

Library:

```python
from scitexlintr import lint_tex, lint_file, load_manifest, apply_fixes
manifest = load_manifest(".manifest.json")
findings = lint_tex(source_string, filename="report.tex", manifest=manifest)
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

For `.tex` reports, scitexlintr parses the source with a small
TeX-aware scanner (comments stripped while preserving byte offsets,
verbatim environments skipped, balanced-brace argument extraction),
builds a "prose mask" that excludes structural-macro arguments
(`\label`, `\ref`, `\cite`, `\includegraphics`, the wrapper macros
themselves), and runs each rule over the prose. Snapshot drift, raw
generated values, unfingerprinted figures, and unsourced numeric
claims are then matched against the manifest's published contract.

## Status

- **R package (v0.1.0)** — 44 rules implemented (R001–R044, including
  R020/R025/R026 cross-file). 155 testthat fixtures passing. `R CMD
  check --as-cran` clean. Tested against real analysis code with a
  ~62% noise reduction from naive matching (after v1.1 tightening).
- **Python package (v0.1.0)** — 27 rules implemented (`broad-exception`,
  `unchecked-merge`, `magic-threshold`, `label-in-blind-stage`,
  `synthetic-data-generation`, …). 139 pytest tests passing. `python -m
  build` produces clean wheel + sdist; `twine check` PASSED.
- **scitexlintr (v0.1.0)** — 10 rules covering manifest-anchored checks
  (`snapshot-mismatch` auto-fixable, `raw-generated-value`,
  `bare-generated-macro`, `unwrapped-threshold`, `unfingerprinted-figure`,
  `unsourced-numeric-token`, `overloaded-term-no-warning`,
  `forbidden-alias`) and manifest-free checks
  (`handwritten-numeric-claim`, `magic-tex-threshold`). 117 pytest
  tests passing. Hand-rolled TeX scanner; no external runtime deps.
  Reviewed twice by automated review (codex) on PR #1; six findings
  addressed across two rounds.

None are on PyPI / CRAN yet — install from this repo via the commands
above. All three are structurally ready for upload when the time
comes.

## See also

- [`analysis_lint_strategy.md`](analysis_lint_strategy.md) — the canonical
  rule spec and design rationale for the analysis-code linters.
- [`docs/failure-modes.md`](docs/failure-modes.md) — catalogued analysis
  and code failure modes that motivate each rule.
- [`r/scilintr/README.md`](r/scilintr/README.md) — R package details.
- [`py/scilintr/README.md`](py/scilintr/README.md) — Python package details.
- [`tex/scitexlintr/README.md`](tex/scitexlintr/README.md) — LaTeX report
  linter: wrapper-macro convention, manifest schema, rule catalog.

## License

MIT.
