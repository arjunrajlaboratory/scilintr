# Failure modes captured by scilintr

Every rule in scilintr was motivated by a real failure mode observed in
scientific data analysis code — patterns that pass tests but produce
wrong, unreproducible, or unreviewable results. This document catalogues
those failure modes and maps each one to the rule(s) that detect it.

## Where the failure modes come from

The bulk of the rule set was synthesized from a multi-month audit of one
internal scientific repository's code reviews. 8 review reports (Apr–May
2026, ~250KB total) surfaced 38 distinct findings across statistical,
engineering, and reporting concerns. Findings clustered into three
buckets — analysis-side bugs (statistical/methodological), code-side
bugs (engineering), and the boundary between the two (code patterns
that produce specific analytical bugs).

Each rule is grounded in at least one concrete failure from those
reviews. The recurrence column below reflects how often a variant of
the pattern showed up across the 8 reports.

## Analysis-side failure modes

### A1. Leakage / circularity (6/8 reviews — dominant theme)

A selector, axis, or null is built from the same labels it then
"validates" against.

| Variant | Rule | Concrete review citation |
|---|---|---|
| Tie-break on a label column | R032 | `order(-score, -is_gt_label)` caught by Codex P1 review |
| Selection-stage file reads label columns | R033 | `df$legacy_branch2_clone` in `selected_calls.R` |
| Output CSV mixes label and score columns | R034 | `module_summary` had `legacy_branch2_clone` co-resident with discovery scores |
| Selection input is a label-tuned summary | R035 | Band parameters tuned to maximize labelled recall, then reused in a "no-circularity" variant |
| Constants defined adjacent to label reads | R036 | Load-bearing VAF band whose width was selected on labels |
| "Blind" function name with label refs in body | R040 | Multiple "Fully unsupervised" / "Honest endpoint" framings on code that joined labels |

### A2. Forking paths / iterative tightening (5/8)

Cascades of rule changes driven by labelled outcomes of prior runs, with
no FWER or FDR control on the meta-selection.

| Variant | Rule |
|---|---|
| Composite score with ≥3 literal weights | R037 |
| Symmetric "best of either side" reporting | R038 |

### A3. Missing uncertainty / inadequate nulls (6/8)

Bare point estimates on integer-valued sparse panels; bootstraps that
mechanically can't move; permutation budgets too thin for tail quantiles.
Mostly a review-level concern; not directly lintable. Covered by
`mycelium:review` rather than scilintr.

### A4. Mechanistic mis-attribution (5/8)

Negative or null results re-framed as "stopping points" or "honest
endpoints" when the cause is upstream. The lintable surface here is
narrow: signed metrics rendered with `pmax(., 0)` (R023) bury the actual
sign of the result on the figure.

## Code-side failure modes

### C1. Helper duplication / shadow-overwrite that grows after consolidation (4/8)

Half-done consolidations make things worse, not better. `_lib.R` made
shadow-overwrites silent in the source repo — helper duplication grew
rather than shrunk after the alias layer was added.

| Variant | Rule |
|---|---|
| `source("_lib.R")` then redefining a sourced name | R020 |
| Same function defined in multiple files | R025 |
| Function defined but never called from any other file | R026 |

### C2. Silent error swallowing (4/8)

The dominant LLM-codegen failure mode.

| Variant | Rule |
|---|---|
| `try(..., silent = TRUE)` | R007 |
| `tryCatch(..., error = function(e) <literal>)` | R030 |

Concrete examples from the source reviews: Wilcoxon failures silently
mapped to `NA_real_`; Firth-GLM separation failures mapped to `NA`;
`fisher.test` FEXACT-workspace failures mapped to `p = 1`. Each
downstream calculation continued with a numerically-valid but
scientifically-meaningless value.

### C3. Magic constants and patient-coded IDs (4/8)

| Variant | Rule |
|---|---|
| Magic threshold in comparison | R002 |
| Hardcoded sample IDs | R016 |
| Patient/sample literal in code declared sample-agnostic | R021 |
| Function-signature default that encodes a scientific choice | R024 |

The most consequential boundary-finding (B1 below) sits here: function
arguments default to `top_modules = 25L` or `target_mode = "lowest"` —
the headline metric depends on it but a reader following the call chain
never sees the choice.

### C4. CLI / env-var validator asymmetry (3/8)

Helpers in the same module mix halting-on-bad-input with
silently-default-on-bad-input. A typo in one env var fails loudly; a
typo in the next passes silently.

| Variant | Rule |
|---|---|
| `env_*` helpers split between halting and defaulting in one file | R027 |

### C5. Doc / STATUS / MANIFEST drift (5/8)

Mostly a review-level concern; not directly lintable. Covered by
`mycelium:review`.

### C6. R-specific footguns

| Variant | Rule |
|---|---|
| `read.csv()` mangles column names containing `-`, `>`, `:` | R029 |
| Silent `tryCatch` swallowing (overlap with C2) | R030 |

## Boundary failure modes — code patterns that produce analytical bugs

### B1. Smuggled defaults driving headline conclusions (6/8 — top recurrence)

A function-signature default that encodes a methodological choice. The
headline metric depends on the default, but the user reading the call
chain never sees it.

Examples from the source reviews:
- `top_modules = 25L` smuggled in three rankers
- `PRIMARY_COLLAPSE_MODE = "lowest"` as canonical; safer `mut_type` was
  opt-in
- Recursive probe hardcoded A191-tuned stability gates at every child
  node
- `make_coverage_absence_call()` used `low_support_max = 0` and
  `high_support_min = 0.60` as caller-side defaults

| Rule | What it catches |
|---|---|
| R024 | Function-signature defaults with non-trivial literal values |
| R039 | Recursive calls that pass a formal through unchanged |

### B2. LOH-blind centering, mean-imputed missing, coverage-as-axis (5/8)

Same misspecification in three independent code surfaces (residual-count
axis, sparse-axis module discovery, spectral binomial residuals). Each
case looked like reasonable code in isolation; the missing context was
"this analysis has LOH loci where the one-population-mean centering
breaks." Domain-specific; not currently captured by scilintr.

### B3. Polarity / collapse-mode mis-orienting carriers (3/8)

`"lowest"` panel-burden collapse mis-oriented point-mutation singletons
in the source repo, directly producing a documented 14/1 EM-tree failure.
Domain-specific; not directly lintable.

### B4. Discovery-on-data scored on data — no OOB (4/8)

`cell_call_stability` is a discovery-stability metric, not a
generalization metric, but its name suggested otherwise. With-replacement
bootstrap further inflated it. Needs cross-file analysis of how the
bootstrap is structured. Beyond v1 scope.

### B5. Label columns co-resident with score columns (3/8)

Structurally enforce the selection-stage / evaluation-stage file split,
so labels never co-reside with scores in a "blind" output file.

| Rule | What it catches |
|---|---|
| R034 | A `data.frame(...)` with both label and score columns followed by `write.csv` in a selection-stage file |

### B6. `set.seed()` inside inner loops polluting RNG (2/8)

`set.seed(191)` inside a function called from `mclapply` resets the RNG
state on every invocation, pinning every "random" axis split to the same
starting condition.

| Rule | What it catches |
|---|---|
| R022 | `set.seed()` inside a function body |

### B7. Definition drift across two implementations (3/8)

Same metric implemented twice, drifting in subtle ways. Diagnostic ΔBIC
differed from library ΔBIC in the source repo; the lineage-like score
had a divergent size-score denominator across files.

| Rule | What it catches |
|---|---|
| R025 | Same function name defined in multiple files |

## Full rule map

Numeric rule IDs are language-agnostic — the "R" prefix stands for
"Rule," not "R the language." The Python package will use the same IDs.

| Rule | Side | Description |
|------|------|-------------|
| R001 | code | Positional dataframe access by integer literal |
| R002 | code | Magic threshold in comparison |
| R003 | code | Join without cardinality check |
| R004 | code | Positional sample alignment |
| R005 | code | Filter/drop without ledger |
| R006 | code | NA coercion / missingness without ledger |
| R007 | code | Broad `try(silent=TRUE)` exception |
| R008 | code | Implicit file selection (`latest_*`, mtime) |
| R009 | code | Cache without input fingerprint |
| R010 | code | Synthetic data in main analysis |
| R011 | code | Stochastic method without seed |
| R012 | analysis | Label reference in blind stage |
| R013 | code | Hardcoded design formula |
| R014 | code | Unexplained transform (ComBat, residualize) |
| R015 | code | Ambiguous Seurat layer/assay |
| R016 | code | Hardcoded sample IDs |
| R017 | code | Warning suppression |
| R018 | code | Model fit without convergence check |
| R019 | code | Filtering inside plot code |
| R020 | code | Shadow-overwrite of sourced helper |
| R021 | both | Patient/sample ID in library code |
| R022 | both | `set.seed()` inside loop/parallel body |
| R023 | both | Plot transform that suppresses range (`pmax(., 0)`) |
| R024 | both | Smuggled function-signature default |
| R025 | code | Cross-file definition drift |
| R026 | code | Dead/unused code |
| R027 | code | Asymmetric env-var validators |
| R028 | both | Partial cache input fingerprint |
| R029 | code | `read.csv()` column-name mangling |
| R030 | code | Silent `tryCatch` swallow |
| R031 | both | Magic eps floor in log/BIC |
| R032 | analysis | Tie-break on label column |
| R033 | analysis | Label reference in selection-stage file |
| R034 | both | Label+score column co-residence in CSV write |
| R035 | analysis | Selection-stage read of label-tainted file |
| R036 | analysis | Threshold defined adjacent to label read |
| R037 | analysis | Composite score with ≥3 literal weights |
| R038 | analysis | "Best of either side" reporting |
| R039 | both | Recursive call with constant gates |
| R040 | analysis | "Blind" function name with label refs in body |
| R041 | code | Return NULL/NA on missing input (silent absence) |
| R042 | code | CLI flag declared but never read |
| R043 | code | Config loaded (`yaml::read_yaml`, `jsonlite::fromJSON`) without schema validation |
| R044 | code | Boolean mask built from empty-string sentinel |

Rules R041–R044 were originally written for the Python sibling
(`py/scilintr/`) and ported to R when the same patterns appeared in
research-R code. Each catches a "silent shrug" — a code path that
treats a missing or malformed input as an acceptable empty signal
instead of failing loudly. R041 was confirmed to fire on a real
`if (!file.exists(f)) return(NULL)` in `build_report.R` during the
smoke test that followed implementation.

## Report-side drift (scitexlintr territory)

A separate class of failure modes lives on the report side, not the
analysis side: a number computed correctly in the analysis becomes
stale by the time it lands in the `.tex` writeup, a figure is
regenerated but the prose still describes the old one, an analysis-side
threshold is relaxed but the abstract still cites the old value.
[`tex/scitexlintr/`](../tex/scitexlintr/README.md) is the linter for
that layer. Its rule catalog — snapshot drift, unfingerprinted figures,
handwritten numeric claims, forbidden aliases, overloaded terms without
a warning — is disjoint from the analysis-code rules above.

## What's not captured

Some failure modes are inherently review-level concerns and don't lend
themselves to static detection. Scilintr is paired with code-review
tooling (e.g., `mycelium:review`) for these:

- Mechanistic mis-attribution at the level of natural-language framing
- Wrong baseline / wrong metric choice
- STATUS / MANIFEST / abstract drift (within the analysis layer;
  scitexlintr catches drift between the analysis result and the report)
- Domain-specific misspecifications (LOH-blind centering, polarity bugs,
  coverage-as-axis)
- "Half-built" pipeline state where the prose is ahead of the code

The lint catches the structural shapes; the review catches the prose
and methodology.
