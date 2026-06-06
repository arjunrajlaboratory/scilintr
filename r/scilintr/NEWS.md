# scilintr 0.1.1

* Initial CRAN release.
* Static analysis for R scientific data-analysis code, flagging patterns
  that often correspond to hidden scientific commitments: silent error
  swallowing, smuggled defaults, label leakage in selection-stage code,
  magic-eps floors in BIC formulas, and shadow-overwrite of sourced
  helpers.
* User-facing entry points: `lint_file()`, `lint_project()`, and the CLI
  wrapper `main()`.
* Structured `ANALYSIS_OK[...]` waivers provide an in-source audit trail
  for intentionally-accepted findings.
