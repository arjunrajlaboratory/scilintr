## Submission

This is a new submission of scilintr (version 0.1.1).

scilintr provides static analysis for R scientific data-analysis code,
flagging patterns that often correspond to hidden scientific commitments
(silent error swallowing, smuggled defaults, label leakage, magic-eps
floors, and shadow-overwrite of sourced helpers).

## Test environments

* local macOS, R 4.6.0 (2026-04-24)

## R CMD check results

`R CMD check --as-cran scilintr_0.1.1.tar.gz` on the built tarball:

```
Status: 2 NOTEs
```

0 errors | 0 warnings | 2 notes

Both NOTEs are benign:

* **checking CRAN incoming feasibility ... NOTE** — "New submission"
  (with the maintainer line). This is the expected note for a first-time
  submission.
* **checking HTML version of manual ... NOTE** — "Skipping checking HTML
  validation: 'tidy' doesn't look like recent enough HTML Tidy." This is
  a property of the local check machine's HTML Tidy version, not of the
  package; it does not occur on the CRAN build machines.

`R CMD check` also ran the examples (including `--run-donttest`) and the
`testthat` suite, both of which passed cleanly.

## Downstream dependencies

There are currently no downstream dependencies (new submission).
