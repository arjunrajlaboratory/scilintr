## Submission

This is a new submission of scilintr (version 0.1.1).

scilintr provides static analysis for R scientific data-analysis code,
flagging patterns that often correspond to hidden scientific commitments
(silent error swallowing, smuggled defaults, label leakage, magic-eps
floors, and shadow-overwrite of sourced helpers).

## Test environments

* local macOS, R 4.6.0 (2026-04-24)
* win-builder, R-devel and R-release (via `devtools::check_win_*`)

## R CMD check results

0 errors | 0 warnings | 1 note

On win-builder (R-devel) the only NOTE is:

* **checking CRAN incoming feasibility ... NOTE** — "New submission"
  (with the maintainer line), as expected for a first-time submission. It
  also lists two "possibly misspelled words" in DESCRIPTION, both of which
  are intentional and spelled correctly:
    * *agentic* — i.e. "agentic coding workflows" (relating to AI coding
      agents); an established term of art in this domain.
    * *eps* — epsilon, the numerical-tolerance floor referred to by
      "magic-eps floors".

The local `R CMD check --as-cran` (macOS, R 4.6.0) additionally emits a
"checking HTML version of manual ... NOTE" ("'tidy' doesn't look like
recent enough HTML Tidy"). That is a property of the local machine's HTML
Tidy version, not of the package, and does not occur on win-builder or the
CRAN build machines.

`R CMD check` also ran the examples (including `--run-donttest`) and the
`testthat` suite, both of which passed cleanly.

## Downstream dependencies

There are currently no downstream dependencies (new submission).
