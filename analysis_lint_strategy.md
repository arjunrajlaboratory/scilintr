# Analysis Lint Strategy for Agentic Scientific Data Analysis

## Purpose

Coding agents are increasingly useful for exploratory analysis, especially in biology, bioinformatics, and RNA-seq workflows. The problem is that many dangerous analysis failures look like reasonable software engineering:

- fallback to an older file when a new file is missing,
- broad exception handling that allows analysis to continue,
- silent row or sample dropping,
- positional column indexing,
- implicit joins,
- hidden label usage in unsupervised analysis,
- random synthetic data generation when real data are unavailable,
- cached outputs reused without checking whether inputs changed,
- thresholds or baselines hard-coded in scattered places.

The lint strategy is a lightweight way to make those decisions visible. It does **not** try to prove that the analysis is correct. Instead, it detects code smells that often correspond to hidden scientific commitments and requires an explicit, reviewable justification.

The core principle is:

```text
Scientifically meaningful choices must not be anonymous.
They must be named, declared, checkpointed, or explicitly justified.
```

## Design point: agent-first

This lint strategy is designed primarily for agentic coding workflows. The primary user is an LLM coding agent; the secondary user is a human reviewer.

This changes the cost-benefit math compared to a human-targeted linter. **False positives are cheap.** An LLM agent can read each finding, decide whether it is a real issue or a legitimate exception, and either fix it or add a structured `ANALYSIS_OK[...]` waiver in a few seconds. There is no developer-fatigue cost to over-flagging, which is what bounds aggressiveness for human-targeted linters.

The design point is therefore **high recall over high precision** — flag anything that *might* be a scientifically meaningful choice, and let the agent (or its reviewer) decide what to do. Many flagged patterns will be legitimate; that is expected and fine. The structured waiver mechanism is the audit trail: every accepted "false positive" becomes a one-line declaration of intent that future readers, reviewers, and downstream agents can scan.

Concrete consequences for rule design:

- Rules can be aggressive about flagging patterns like function-signature defaults, `tryCatch` swallowing, magic constants, label-near-selection co-residence, and shadow-overwrite — even when the specific instance is fine.
- The waiver overhead per accepted exception is small (one structured comment) compared to the value of having an explicit, machine-grepable record of every consequential choice.
- Recall failures (missed real bugs) are more costly than precision failures (flagged-but-fine code). The opposite tradeoff from a human-targeted linter like `lintr` or `flake8`.
- A finding that an agent dismisses with a waiver still adds value: the next agent (or the human reviewer) sees the structured intent declaration and doesn't have to re-derive it.

Humans can still use these linters — the structured waiver mechanism is helpful in code review either way — but the design tradeoffs (recall > precision, aggressive structural pattern matching, fine-grained category vocabulary) are tuned for an agent-driven loop where the cost of "look at this and decide" is near zero.

## High-level strategy

Use a project-specific scientific linter that scans code for suspicious analysis patterns. The linter is cheap and should run frequently: during agent iterations, in pre-commit hooks, in CI, or before a coding agent reports a result.

The linter should be stage-aware. It should know, for example, which files belong to blind QC, data loading, differential expression, plotting, report generation, or test fixtures.

A typical command might be:

```bash
make quick-check
```

with:

```makefile
quick-check:
	python tools/code_scientific_lint.py
	python tools/latex_scientific_lint.py
	python tools/run_fast_canaries.py
```

The linter should not permanently ban every suspicious operation. Instead, it should require a structured escape comment when the operation is scientifically intentional.

## Structured escape comments

The escape mechanism should be explicit and structured. A generic waiver such as this should not pass:

```python
# ANALYSIS_OK
metadata = metadata.dropna()
```

Nor should this:

```python
# ANALYSIS_OK: fine
metadata = metadata.dropna()
```

A useful waiver should answer three questions:

1. **What is being changed?**
2. **Why is it scientifically valid?**
3. **Where is it recorded, asserted, or checked?**

Recommended format:

```python
# ANALYSIS_OK[category]: explanation; check/ledger/assertion location
```

Examples:

```python
# ANALYSIS_OK[filtering]: remove genes with total counts below MIN_TOTAL_COUNTS_PER_GENE;
# no samples removed; summary written to build/gene_filter_summary.tsv
expr = expr.loc[gene_filter, :]
```

```python
# ANALYSIS_OK[join]: one-to-one sample_id join; validate='one_to_one';
# sample set asserted immediately below
metadata = metadata.merge(batch_info, on="sample_id", how="left", validate="one_to_one")
```

```python
# ANALYSIS_OK[label-annotation-only]: treatment is joined only after PCA coordinates are fixed;
# used for plot color only, not for computing PCA
pca_plot = pca_coords.merge(labels[["sample_id", "treatment"]], on="sample_id", validate="one_to_one")
```

```python
# ANALYSIS_OK[api-retry]: retry same dataset_id only after transient API error;
# no alternate dataset fallback is used
try:
    counts = fetch_counts(dataset_id)
except TransientAPIError:
    counts = fetch_counts(dataset_id)
```

```python
# ANALYSIS_OK[random-seed-only]: seed for stochastic UMAP; no synthetic data generated
RANDOM_SEED = 20260523
```

The point is not that the comment proves correctness. The point is that it creates a small, reviewable scientific statement.

## Suggested waiver categories

A starter set of categories:

```text
ANALYSIS_OK[filtering]
ANALYSIS_OK[sample-filter]
ANALYSIS_OK[feature-filter]
ANALYSIS_OK[join]
ANALYSIS_OK[positional-access]
ANALYSIS_OK[missingness]
ANALYSIS_OK[imputation]
ANALYSIS_OK[label-annotation-only]
ANALYSIS_OK[label-needed-for-supervised-model]
ANALYSIS_OK[contrast-definition]
ANALYSIS_OK[api-retry]
ANALYSIS_OK[file-selection]
ANALYSIS_OK[cache]
ANALYSIS_OK[random-seed-only]
ANALYSIS_OK[permutation-test]
ANALYSIS_OK[bootstrap]
ANALYSIS_OK[synthetic-test-fixture]
ANALYSIS_OK[simulation-only]
ANALYSIS_OK[canary-corruption]
ANALYSIS_OK[batch-correction]
ANALYSIS_OK[normalization]
ANALYSIS_OK[warning-suppression]
ANALYSIS_OK[model-fit]
```

Different projects can tune this list.

## Stage-aware lint configuration

A lightweight YAML config can tell the linter which files belong to which stage and what rules apply.

Example:

```yaml
stages:
  blind_qc:
    files:
      - scripts/run_blind_qc.py
      - scripts/qc_helpers.py
      - notebooks/blind_qc.ipynb
    label_policy: forbidden
    suspicious_patterns:
      - dropna
      - fillna
      - merge
      - join
      - iloc
      - try
      - except
      - np.random

  data_boundary:
    files:
      - scripts/load*
      - scripts/fetch*
      - scripts/prepare*
    suspicious_patterns:
      - try
      - except
      - fallback
      - backup
      - previous
      - latest
      - glob
      - file.exists
      - dropna
      - inner_join
      - merge
      - np.random

  supervised_modeling:
    files:
      - scripts/run_de.py
      - scripts/run_model.py
    label_policy: allowed
    suspicious_patterns:
      - contrast
      - formula
      - random_state
      - KMeans
      - UMAP
```

The linter can be implemented with regular expressions at first, then gradually upgraded with AST-based checks for Python or language-specific parsing for R.

## Explicit label declaration

A separate label declaration file helps the linter detect label leakage programmatically.

Example:

```yaml
# analysis_labels.yml

label_sources:
  - name: sample_labels
    kind: file
    path: data/sample_labels.tsv
    role: biological_labels

labels:
  treatment:
    role: experimental_condition
    source: sample_labels
    column: treatment
    column_index: 3
    values:
      - control
      - treated
    synonyms:
      - condition
      - group
      - arm
      - treatment_group
      - tx

  diagnosis:
    role: phenotype
    source: sample_labels
    column: diagnosis
    values:
      - healthy
      - disease
    synonyms:
      - phenotype
      - disease_status
      - case_control
      - status

allowed_blind_covariates:
  - sample_id
  - batch
  - lane
  - donor
  - rin
  - library_prep
```

The linter can then flag label files, label columns, label values, and label synonyms in forbidden stages.

For example, in a blind PCA computation file, these should be suspicious:

```python
metadata["treatment"]
metadata["condition"]
metadata.query("group == 'treated'")
adata.obs["response"]
```

Also suspicious:

```python
metadata.iloc[:, 3]
```

if column index 3 is declared as a label column.

## Recommended lint categories and examples

### 1. Raw positional column or row access

Flag anonymous positional indexing:

```python
condition = metadata.iloc[:, 3]
batch = metadata.iloc[:, 2]
expr = counts.iloc[:, 5:]
adata.obs.iloc[:, 4]
```

R examples:

```r
condition <- metadata[, 4]
batch <- metadata[[3]]
expr <- counts[, 6:ncol(counts)]
```

Better:

```python
TREATMENT_COL = "treatment"
condition = metadata[TREATMENT_COL]
```

If positional access is unavoidable, require a named constant and an assertion:

```python
TREATMENT_COL_INDEX = 3
assert metadata.columns[TREATMENT_COL_INDEX] == "treatment"
condition = metadata.iloc[:, TREATMENT_COL_INDEX]
```

In blind stages, positional metadata access should be especially suspicious.

### 2. Magic thresholds and anonymous scientific numbers

Flag hard-coded thresholds in analysis logic:

```python
res = res[res["padj"] < 0.05]
expr = expr[expr.sum(axis=1) > 10]
hvg = select_top_genes(expr, 2000)
outliers = zscores > 3
```

Better:

```python
FDR_THRESHOLD = 0.05
MIN_TOTAL_COUNTS_PER_GENE = 10
N_HIGHLY_VARIABLE_GENES = 2000
OUTLIER_Z_THRESHOLD = 3

res = res[res["padj"] < FDR_THRESHOLD]
```

Or from config:

```yaml
thresholds:
  fdr: 0.05
  min_total_counts_per_gene: 10
  n_highly_variable_genes: 2000
```

This is not about banning thresholds. It is about making them named and reviewable.

### 3. Joins and merges without cardinality checks

Flag:

```python
metadata = metadata.merge(batch_info, on="sample_id")
```

Prefer:

```python
metadata = metadata.merge(
    batch_info,
    on="sample_id",
    how="left",
    validate="one_to_one",
)
assert metadata["sample_id"].is_unique
```

R examples to flag:

```r
metadata <- left_join(metadata, batch_info)
```

Prefer:

```r
metadata <- left_join(metadata, batch_info, by = "sample_id")
stopifnot(!anyDuplicated(metadata$sample_id))
```

For analysis data, joins should usually declare:

- join key,
- join direction,
- expected cardinality,
- whether sample sets are allowed to change.

### 4. Positional sample alignment

Flag patterns where sample identity is inferred by order:

```python
metadata = metadata.iloc[:counts.shape[1]]
counts.columns = metadata["sample_id"]
expr_values = expr.to_numpy()
labels = metadata["condition"].to_numpy()
expr = expr[:, metadata.index]
```

Better:

```python
# ANALYSIS_OK[id-alignment]: samples are explicitly reordered by sample_id and asserted below
expr = expr.loc[:, metadata["sample_id"]]
assert list(expr.columns) == list(metadata["sample_id"])
```

This is a high-priority lint rule for omics workflows.

### 5. Filtering, dropping, and subsetting

Flag:

```python
metadata = metadata.dropna()
metadata = metadata[metadata["qc_pass"]]
expr = expr[:, keep_samples]
expr = expr[keep_genes, :]
```

R examples:

```r
metadata <- na.omit(metadata)
metadata <- metadata[metadata$qc_pass, ]
expr <- expr[, keep_samples]
```

Filtering can be valid, but it should be named and recorded.

Better:

```python
# ANALYSIS_OK[sample-filter]: remove samples that failed predeclared sequencing QC;
# recorded in build/dropped_samples.tsv
metadata = metadata.loc[metadata["qc_status"] == "pass"]
```

Or use a helper that writes a drop ledger:

```python
metadata = filter_samples(
    metadata,
    keep=metadata["qc_status"] == "pass",
    reason="failed sequencing QC",
    ledger="build/dropped_samples.tsv",
)
```

### 6. Missingness, imputation, and coercion

Flag:

```python
df = df.fillna(0)
df = df.dropna()
x = np.nan_to_num(x)
df["age"] = pd.to_numeric(df["age"], errors="coerce")
```

R examples:

```r
df <- tidyr::replace_na(df, 0)
df <- na.omit(df)
x <- as.numeric(x)
```

Allowed only with explanation:

```python
# ANALYSIS_OK[missingness]: samples missing the design variable are excluded;
# exclusions recorded in build/dropped_samples.tsv
metadata = metadata.dropna(subset=["treatment"])
```

or:

```python
# ANALYSIS_OK[imputation]: missing library_prep is set to 'unknown' for plotting only;
# not used in the DE model
metadata["library_prep"] = metadata["library_prep"].fillna("unknown")
```

### 7. Broad exception handling and fallback logic

Flag:

```python
try:
    counts = load_counts(new_path)
except Exception:
    counts = load_counts(old_path)
```

```python
try:
    metadata = load_metadata(path)
except:
    pass
```

R examples:

```r
try(..., silent = TRUE)
tryCatch(..., error = function(e) NULL)
```

Broad exception handling should be nearly forbidden in data loading and analysis preparation.

Allowed:

```python
# ANALYSIS_OK[api-retry]: retry same dataset_id after transient API error;
# no alternate dataset fallback
try:
    counts = fetch_counts(dataset_id)
except TransientAPIError:
    counts = fetch_counts(dataset_id)
```

Fallbacks to old, backup, previous, default, or synthetic data should be hard failures unless explicitly part of a declared test fixture.

### 8. Implicit file selection

Flag:

```python
files = glob("data/*.csv")
path = sorted(files)[-1]
path = max(files, key=os.path.getmtime)
counts = pd.read_csv("data/latest_counts.tsv")
counts = pd.read_csv("data/counts_old.tsv")
```

Suspicious words in paths or variables:

```text
latest
old
backup
previous
tmp
temp
copy
archive
final_final
```

Better:

```python
DATA_RELEASE = "rnaseq_release_2026_05_22"
COUNTS_PATH = f"data/{DATA_RELEASE}/counts.tsv"
```

or:

```python
# ANALYSIS_OK[file-selection]: latest_counts.tsv is a stable symlink maintained by data registry;
# input fingerprint checked immediately below
```

### 9. Caching without input fingerprints

Flag:

```python
if output.exists():
    return pd.read_csv(output)
```

Better:

```python
if cache_is_valid(output, inputs=[counts_path, metadata_path, config_path]):
    return load_cached(output)
```

Agent-generated analysis code often introduces caching to speed up workflows. That is useful, but stale cache reuse is dangerous.

### 10. Randomness and synthetic data generation

Randomness should be a core lint category.

Separate two cases:

```text
1. Randomness used by a stochastic method.
   Example: UMAP, t-SNE, k-means, train/test split, bootstrap.
   Allowed, but must be seeded and recorded.

2. Randomness used to create data-like objects.
   Example: random counts, random metadata, random expression matrices.
   Forbidden in main analysis unless explicitly marked as simulation, test fixture, or canary.
```

Flag Python patterns:

```text
np.random
numpy.random
random.
default_rng
rng.normal
rng.uniform
rng.poisson
rng.binomial
rng.choice
rng.permutation
rng.shuffle
torch.rand
torch.randn
tf.random
scipy.stats.*.rvs
sklearn.datasets.make_*
Faker
```

Flag R patterns:

```text
rnorm
runif
rpois
rbinom
sample
sample_n
sample_frac
replicate
simulate
matrix(rnorm(...))
```

This should fail in main analysis:

```python
counts = np.random.poisson(10, size=(20000, 48))
```

This should also fail:

```python
if not counts_path.exists():
    counts = np.random.normal(size=(1000, 12))
```

Allowed canary example:

```python
# ANALYSIS_OK[canary-randomization]: permutes declared labels only in a temporary test fixture;
# never used as real input data
rng = np.random.default_rng(CANARY_SEED)
labels["treatment"] = rng.permutation(labels["treatment"].to_numpy())
```

Allowed stochastic method:

```python
RANDOM_SEED = 20260523
embedding = UMAP(random_state=RANDOM_SEED).fit_transform(expr)
```

Flag random generation assigned to data-like variables:

```python
expr = rng.normal(...)
counts_df = pd.DataFrame(np.random.poisson(...))
adata = AnnData(np.random.normal(...))
metadata["treatment"] = rng.choice(...)
```

Such code should only be allowed in tests, canaries, simulations, or explicit null models.

### 11. Stochastic methods without seeds

Flag:

```python
UMAP().fit_transform(expr)
TSNE().fit_transform(expr)
KMeans(n_clusters=5).fit(expr)
train_test_split(x, y)
```

Prefer:

```python
RANDOM_SEED = 20260523
UMAP(random_state=RANDOM_SEED).fit_transform(expr)
KMeans(n_clusters=5, random_state=RANDOM_SEED).fit(expr)
train_test_split(x, y, random_state=RANDOM_SEED)
```

R workflows should similarly require `set.seed(...)` near stochastic operations.

### 12. Label words in blind stages

Using `analysis_labels.yml`, flag label-related terms in blind or unsupervised stages:

```text
treatment
condition
phenotype
diagnosis
response
outcome
case
control
treated
responder
contrast
label
class
group
```

Especially in files or functions named:

```text
blind
qc
pca
umap
tsne
embedding
cluster
neighbors
hvg
variable_gene
normalize
```

Bad:

```python
genes = select_genes_associated_with(metadata["treatment"])
pca = PCA().fit_transform(expr[genes])
```

Allowed only after computation:

```python
pca_coords = compute_pca(expr)

# ANALYSIS_OK[label-annotation-only]: treatment is used only for plot color after PCA coordinates are fixed
pca_plot = pca_coords.merge(labels[["sample_id", "treatment"]], on="sample_id", validate="one_to_one")
```

### 13. Design formulas and contrasts

Flag hard-coded design formulas and contrasts:

```python
formula = "~ treatment + batch"
contrast = ("treatment", "treated", "control")
```

R:

```r
design = ~ treatment + batch
contrast = c("treatment", "treated", "control")
```

Prefer config:

```yaml
de_model:
  formula: "~ treatment + batch"
  factor: treatment
  target: treated
  reference: control
  positive_logfc_means: higher expression in treated
```

The code and report should read from this single source.

### 14. Batch correction, residualization, and normalization

Flag scientifically consequential transforms:

```python
combat(...)
regress_out(...)
remove_batch_effect(...)
residualize(...)
np.log1p(counts)
zscore(x)
counts / counts.sum(axis=0)
```

Allowed with explanation:

```python
# ANALYSIS_OK[batch-correction]: remove sequencing batch only;
# treatment is not included as a batch covariate
expr_corrected = combat(expr, batch=metadata["batch"])
```

```python
# ANALYSIS_OK[normalization]: CPM normalization for exploratory PCA only
x = counts / counts.sum(axis=0) * 1e6
```

### 15. AnnData and Seurat layer ambiguity

Flag ambiguous access:

```python
adata.X
adata.raw.X
adata.layers["counts"]
adata.layers["lognorm"]
```

Better:

```python
EXPRESSION_LAYER_FOR_PCA = "lognorm"
x = adata.layers[EXPRESSION_LAYER_FOR_PCA]
```

R / Seurat example:

```r
GetAssayData(obj)
```

Prefer:

```r
GetAssayData(obj, assay = "RNA", layer = "counts")
```

The goal is to force the layer or assay choice to be explicit.

### 16. Hard-coded sample IDs

Flag:

```python
exclude = ["S17", "S23"]
metadata = metadata[~metadata["sample_id"].isin(exclude)]
```

Allowed only with explanation and ledger:

```python
# ANALYSIS_OK[sample-exclusion]: S17 and S23 failed predeclared sequencing QC;
# see build/dropped_samples.tsv
exclude = ["S17", "S23"]
```

### 17. Warning suppression

Flag:

```python
warnings.filterwarnings("ignore")
```

R:

```r
suppressWarnings(...)
suppressMessages(...)
```

Allowed only narrowly:

```python
# ANALYSIS_OK[warning-suppression]: suppress known plotting font warning only;
# data/model warnings are not suppressed
```

### 18. Model convergence and failed fits

Flag model fitting code that ignores convergence diagnostics when those diagnostics exist.

Suspicious:

```python
model.fit(x, y)
```

Better:

```python
model.fit(x, y)
assert model.converged_
```

or:

```python
# ANALYSIS_OK[model-fit]: convergence checked in build/model_fit_summary.tsv
```

This is especially relevant for downstream modeling, mixed models, and iterative fits.

### 19. Plotting code that changes data

Flag filtering inside plotting code:

```python
plot_df = df[df["padj"] < 0.05]
plot_df = plot_df.dropna()
```

Allowed with explanation:

```python
# ANALYSIS_OK[plot-filter]: volcano labels only; does not affect DE results
plot_df = df[df["padj"] < FDR_THRESHOLD]
```

The linter should distinguish visual filtering from analysis-population filtering.

## Rules derived from recent SNP-tree reviews

The next twelve rules were synthesized from a categorization of eight `mycelium:review` reports across Apr–May 2026 on this project. Each cites the cluster of review findings that motivated it (e.g. "C1, 4/8 reviews" = code cluster 1, flagged in 4 of the 8 reviewed reports). The pattern names match the synthesis in `REPORT_IMPROVEMENT.md` so the provenance is checkable.

### 20. Shadow-overwrite of sourced helpers

**R-specific.** A script that calls `source("_lib.R")` and then redefines names already defined by `_lib.R` silently shadows the library. Future bug fixes that land in `_lib.R` will not propagate; the consuming script silently keeps its stale copy.

This appeared in the SNP-tree codebase after a consolidation pass (cluster C1, 4/8 reviews): scripts continued to redefine helpers below the `source()` call, leaving the alias layer cosmetic. Across two consecutive reviews, helper duplication grew rather than shrunk (14 → 17 file-occurrences of `bind_rows_fill`; 9 → 19 of another helper) after `_lib.R` was added.

Flag (R):

```r
source("_lib.R")
...
score_module <- function(...) { ... }   # if _lib.R also defines score_module, this shadows
```

Linter sketch:

1. Parse every `source(...)` / `sys.source(...)` target in the file.
2. Collect top-level `function(...)` assignments in each sourced file.
3. Collect top-level function assignments in the importing file.
4. Flag any name overlap.

Python analogue: a `from utils import *` (or named import) followed by a top-level redefinition of the same name. Less common but worth catching.

Allowed only with structured waiver:

```r
# ANALYSIS_OK[shadow-overwrite]: local score_module overrides _lib.R::score_module
# because this analysis uses the older v1 form; rationale in NOTES.md
score_module <- function(...) { ... }
```

### 21. Patient / sample / batch IDs hardcoded in library code

A numeric or string literal that matches a value declared as a sample, patient, or batch identifier should be flagged when it appears in code that is declared sample-agnostic (cluster C3, 4/8 reviews).

SNP-tree had `seed = 191L` baked inside `axis_seed_split()` — patient ID buried in a k-means initialization in code framed as a library helper. Similarly, A191-specific SNP coordinates appeared inside a "sample-agnostic" ranker.

Declare identifiers in a manifest:

```yaml
# analysis_identifiers.yml
sample_ids:
  - "A191"
  - "A193"
  - 191
  - 193
forbidden_in:
  - algorithms/**/*.R
  - algorithms/**/*.py
  - "**/_lib.R"
```

The linter greps the forbidden files for any literal in `sample_ids`. This catches the case where a per-sample analysis literal silently makes a "library" function sample-specific.

Allowed with structured waiver:

```r
# ANALYSIS_OK[sample-specific-default]: 191L is a sample-specific seed default for the
# A191-only diagnostic in this script; library function takes seed as an argument.
A191_DEFAULT_SEED <- 191L
```

### 22. `set.seed()` inside loops or parallel workers

Calling `set.seed(...)` inside a function body that is invoked from `lapply` / `mclapply` / `pbmcapply::pbmclapply` / `parallel::mclapply` / a `for` / `while` loop resets the RNG on every invocation. Either (a) the loop's randomness collapses to a single deterministic answer, or (b) the outer RNG stream the loop driver expected to control gets clobbered (cluster B6, 2/8 reviews).

In SNP-tree, `axis_seed_split()` called `set.seed(191)` on every invocation, polluting the bootstrap RNG state and pinning every "random" axis split to the same starting condition.

Flag (R):

```r
my_function <- function(...) {
  set.seed(SOME_SEED)   # flag if this function is called inside a loop / mclapply
  ...
}
```

Flag (Python):

```python
def my_function(...):
    np.random.seed(SEED)
    rng = np.random.default_rng(SEED)
```

Cheap heuristic version: flag any `set.seed(...)` not at the top level of a script (i.e. inside any function body).

Allowed with structured waiver:

```r
# ANALYSIS_OK[seed-inside-fn]: reseeding on every call is intentional because this
# function is the per-task entry point for reproducible parallel work; outer RNG is
# pinned via L'Ecuyer streams.
```

### 23. Plot transforms that suppress informative ranges

A plot transform that monotonically clips a signed metric to its "expected" sign or range can hide negative or out-of-range results. The transform lives in plotting code, but the consequence is that a reader takes home the wrong-signed conclusion (cluster A4 sub-finding from the 2026-05-19 handoff review, F3).

In SNP-tree, a recursive probe's negative ARI (`-0.015`) was rendered as a `0.00` bar with a `0.00` printed label because the plotting code used `pmax(value, 0)` to "make the y-axis start at zero." The negative result became indistinguishable from a null result on the figure.

Flag (R):

```r
pmax(value, 0)
ylim(0, NA)
scale_y_continuous(limits = c(0, NA))
log(value)            # if value can be <= 0
log1p(value)          # if value can be < -1
coord_cartesian(ylim = c(0, ...))    # without a break mark
```

Flag (Python):

```python
np.maximum(value, 0)
plt.ylim(0, None)
ax.set_yscale("log")     # if value can include zeros or negatives
np.log(value)
```

Higher-signal: flag these especially when the variable being plotted has a signed-quantity name (`ari`, `delta`, `effect`, `lift`, `log_ratio`, `correlation`, `coef`, `residual`, `score_diff`).

Allowed with structured waiver:

```r
# ANALYSIS_OK[plot-transform]: pmax(., 0) used only in a log-axis sub-panel;
# the signed-range panel beside it shows the full distribution.
```

### 24. Function-signature defaults for scientifically meaningful choices

A function argument with a default value that encodes a scientific or methodological choice is a smuggled default. The headline metric depends on the default, but the default is invisible to a reader following the call chain in scripts.

This was the most consequential code-meets-analysis finding (cluster B1, 6/8 reviews):

- `top_modules = 25L` smuggled as a function-signature default in three rankers.
- `PRIMARY_COLLAPSE_MODE = "lowest"` as the canonical default while the safer `mut_type` mode was opt-in.
- The recursive probe hardcoded the A191-tuned stability gates at every recursive node.
- `make_coverage_absence_call()` used caller-side hardcoded `low_support_max = 0` and `high_support_min = 0.60`.

Flag (R):

```r
rank_modules <- function(modules, top_modules = 25L, ...) { ... }
collapse_branch <- function(panel, mode = "lowest", ...) { ... }
score_module <- function(panel, support_min = 0.60, ...) { ... }
```

Flag (Python):

```python
def rank_modules(modules, top_modules=25, ...): ...
def collapse_branch(panel, mode="lowest", ...): ...
def score_module(panel, support_min=0.60, ...): ...
```

Linter heuristic: flag function argument defaults that are not `NULL` / `None` / `TRUE` / `FALSE` / `""` / `c()` / `[]`, when the function lives in a file declared as "analysis library" rather than "config." Numeric defaults, non-empty string defaults, and vector defaults are the highest-signal patterns.

Allowed with structured waiver:

```r
# ANALYSIS_OK[smuggled-default]: top_modules = 25L is the pre-declared primary value;
# recorded in decisions_pre_run.md; CSV outputs carry an is_primary flag.
rank_modules <- function(modules, top_modules = 25L, ...) { ... }
```

The strong remediation is to require declared defaults to be loaded from a config file that the report cites by hash.

### 25. Cross-file definition drift

Functions with the same name defined in more than one file are drift hazards. Each independent copy can be edited separately (cluster B7, 3/8 reviews).

In SNP-tree, the diagnostic-level `ΔBIC` definition drifted from the library-level `ΔBIC` definition, and the lineage-like score was implemented twice with a divergent size-score denominator.

Linter sketch:

1. Index all top-level function names: `name -> [files]`.
2. Flag any name with `len(files) > 1`.

R-specific note: R has no namespace system for project scripts, so the drift surface is the whole project tree. Python projects with explicit module boundaries usually catch this naturally — for Python, only flag when the same name is defined in two files that are both imported by some third file.

Allowed with structured waiver:

```r
# ANALYSIS_OK[multi-definition]: two implementations are intentional —
# `score_v1` is referenced only by the historical reproduction script.
```

### 26. Dead / unused code

A function defined but never called is dead code. Each one is a latent confusion source for a future reader, and a maintenance trap when the live code drifts away from it (cluster C6, 2/8 reviews).

SNP-tree shipped `score_burden`, `score_mixture`, and `pc_rank_by_evidence_weighted_recurrence` as defined-and-unreferenced across successive review rounds.

Linter sketch:

1. Index top-level function names defined in project files.
2. For each, grep for callers anywhere in the project tree, excluding the file of definition.
3. Flag with zero callers.

This rule has a higher false-positive rate in R than in Python (R has no module system, so "called from outside" means any other `.R` file, and dynamic dispatch / `do.call` calls can be missed). Treat it as warning-level rather than hard-fail.

### 27. Asymmetric CLI / env-var validators

Within a single module, helper functions that read environment variables or command-line arguments should fail consistently — either all silently default on bad input, or all halt loudly. Asymmetric helpers create cliff edges where one typo halts and another silently uses a default (cluster C4, 3/8 reviews).

In SNP-tree, `env_integer` and `env_number` silently reverted to defaults on invalid input while `env_methods` and `env_family_rule` halted. A typo in `A191_STABILITY_BAND_NCOV_MIN` passed silently; a typo in `A191_STABILITY_FAMILY_RULE` failed loudly.

Linter sketch:

1. Find all helpers named like `env_*` / `get_env_*` / `_arg_*` in the same source file.
2. For each, determine whether it has a fall-through branch (returns a default on bad input) or always raises.
3. Flag the module if it contains both styles.

The lint is about consistency, not about which style is correct. Separately, CLI parsers that accept only `--flag=value` and silently ignore `--flag value` and typos should be flagged (also observed in SNP-tree).

### 28. Partial cache input fingerprints

Extends rule 9. A cache key that fingerprints only a subset of the real inputs can silently return stale outputs when the un-fingerprinted inputs change.

In SNP-tree, a cache validated `idx_e` only, not the underlying `N` / `Y` matrices. Rebuilt test sets returned stale log-likelihoods because `N` / `Y` had been updated but `idx_e` had not. A separate cache had a shard-combine that did not dedup re-runs by `run_id`, so re-running shards inflated downstream counts.

Linter heuristic: if a function reads from multiple inputs but the cache key string mentions fewer of them, flag. This is fuzzy and likely warning-level only.

Allowed with structured waiver:

```r
# ANALYSIS_OK[cache-fingerprint]: idx_e is the only input that varies in this analysis;
# N and Y are pinned by the dataset commit hash and validated upstream by a separate
# fingerprint check.
```

### 29. R-specific: `read.csv()` column-name mangling

R's `read.csv()` mangles column names: `-` and `>` and `:` become `.`, and a name starting with a digit gets prefixed with `X`. So a column named `17-38733306C>T` in the file becomes `X17.38733306C.T` in the dataframe.

If a script does `read.csv(...)` and then references columns by names containing those characters or starting with a digit, every reference is a silent zero-match. SNP-tree carries an entire SNP-naming convention layer (`parse_snp_names`, `convert_raw_to_cache`) precisely to defend against this.

Flag (R):

```r
df <- read.csv("snp_panel.csv")
df[["17-38733306C>T"]]    # silent zero-match — column was mangled to X17.38733306C.T
df$`17-38733306C>T`       # silent zero-match
```

Linter sketch:

1. Find `read.csv(...)` / `read.table(...)` calls without `check.names = FALSE`.
2. In the same script, find column references containing `-`, `>`, `:`, or starting with a digit.
3. Flag.

Better:

```r
df <- read.csv("snp_panel.csv", check.names = FALSE)
df[["17-38733306C>T"]]    # works
```

Or, more robust:

```r
df <- readr::read_csv("snp_panel.csv")    # readr preserves names by default
```

### 30. R-specific: silent `tryCatch` error-swallowing

The R-specific extension of rule 7. The dominant LLM-codegen failure mode in this codebase (cluster C2, 4/8 reviews).

Flag:

```r
result <- tryCatch(risky_op(), error = function(e) NA)
result <- tryCatch(risky_op(), error = function(e) NULL)
result <- tryCatch(risky_op(), error = function(e) 0)
result <- tryCatch(risky_op(), error = function(e) data.frame())
try(risky_op(), silent = TRUE)
```

This pattern showed up repeatedly: `tryCatch` errors silently mapping Wilcoxon failures to `NA_real_`, Firth-GLM convergence/separation failures to `NA`, `fisher.test` FEXACT-workspace-exceeded failures to `p = 1`. Each downstream calculation then continued with a numerically-valid but scientifically-meaningless value.

Related pattern caught by the same lint: `a191_finite_or_zero(x)` style helpers that map `NA` / `NaN` / `Inf` to `0` inside score components. Same shape — silent normalisation of failure into a numerically-valid value.

Better:

```r
result <- tryCatch(
  risky_op(),
  error = function(e) {
    warning("risky_op failed for ", id, ": ", conditionMessage(e))
    structure(NA_real_, error = conditionMessage(e), id = id)
  }
)
# downstream code checks attr(result, "error") explicitly
```

Allowed with structured waiver:

```r
# ANALYSIS_OK[tryCatch-NA]: Firth separation is expected on ~0.5% of candidates;
# NAs logged to build/firth_failures.tsv and excluded with explicit count in the
# supplement.
result <- tryCatch(
  firth_fit(x, y),
  error = function(e) { log_failure(id, conditionMessage(e)); NA_real_ }
)
```

### 31. Magic-eps floors in log / BIC / likelihood formulas

A `pmax(x, eps)` immediately before `log()` is a numerical-stability landmine when the floor is below the data's natural discretisation. The floor then dominates the formula and confuses score comparisons.

In SNP-tree, a BIC variance-floor of `1e-12` was hit by rate-burden values on `{0, 1/k, 2/k, ...}` for small `k` and dominated the ranking output. The fix was a domain-motivated floor (half the smallest non-zero increment), not a numerical-safety constant.

Flag (R):

```r
log(pmax(x, 1e-12))
log(pmax(x, .Machine$double.eps))
log1p(pmax(x, 1e-10))
```

Flag (Python):

```python
np.log(np.maximum(x, 1e-12))
np.log(np.clip(x, 1e-12, None))
```

The pattern to look for: a magic small constant inside `pmax` / `np.maximum` / `np.clip` whose value is not justified by the data's discretisation or measurement resolution. Especially flag these constants inside scoring formulas where score *differences* (e.g. likelihood ratios, BIC deltas) are the eventual headline metric — a constant floor that's hit by some inputs but not others biases those differences.

Allowed with structured waiver:

```r
# ANALYSIS_OK[log-floor]: 1e-12 is below the discretisation grid; floor sensitivity
# tested in bimodality_varfloor_sanity.R, ranking unchanged for floor in [1e-15, 1e-9].
log_x <- log(pmax(x, 1e-12))
```

## Leakage-detection lint rules

Full label-leakage detection requires a more complex blinding-aware harness (covered in the follow-up track). But many leakage patterns are detectable as code smells without running anything. These rules target patterns where ground-truth or label information is *structurally* available to a selection-stage computation, regardless of whether the author noticed. Structural checks are cheap and high-precision.

A stage tag (`selection` vs `evaluation`) on each file is the load-bearing input for most of these rules. The stage config in the earlier YAML example needs one more field:

```yaml
stages:
  selection:
    files:
      - analysis/*/run_*select*.R
      - analysis/*/score_*.R
      - analysis/*/run_root_stage.R
      - analysis/*/run_branch_stage.R
    label_policy: forbidden
  evaluation:
    files:
      - analysis/*/evaluate_*.R
      - analysis/*/make_figures.R
    label_policy: allowed
```

### 32. Tie-break on a label or ground-truth column

Pattern: a secondary sort key that matches a declared label column. The primary score decides ranking; the tie-breaker decides ranking *for ties*; and the tie-breaker is the answer.

In SNP-tree, `order(-score, -is_gt_label)` ranked GT-positive SNPs higher when scores tied. The headline panel had no ties at the boundary K cuts, but a panel-subsampled bootstrap sweep had two reps where ties fired and yielded a spurious `+1 buried_gt_top30` recovery. Post-fix sweep was uniformly `0/60`. The lint catches this *before* the bootstrap reveals it.

Flag (R):

```r
order(-score, -is_gt_label)
arrange(df, desc(score), desc(is_gt))
df[order(df$score, -df$is_target), ]
```

Flag (Python):

```python
df.sort_values(["score", "is_gt"], ascending=[False, False])
df.sort_values(["score", "is_target"], ascending=False)
```

Cheap rule: any `order(...)` / `arrange(...)` / `sort_values([...])` with a secondary key whose name appears in `analysis_labels.yml` or matches `is_gt_*`, `is_target`, `truth_*`, `is_label_*`, `gt_*`, or the column-name of any declared label.

No waiver acceptable in selection-stage files. In evaluation-stage files, allowed with a waiver explaining why the secondary key isn't an answer key:

```r
# ANALYSIS_OK[tie-break]: deterministic SNP-ID tie-break for downstream join stability;
# is_gt is NOT in the sort key.
df <- df[order(-df$score, df$snp_id), ]
```

The generalisable rule is: any `order(-x, ±label_col)` or `arrange(..., label_col)` in scientific code is a leak; use a leak-free tie-breaker (upstream rank from a prior independent analysis, lexicographic ID, or a deterministic random seed).

### 33. Label-column reference in a selection-stage file

Pattern: any reference to a column declared in `analysis_labels.yml` from inside a file declared `stage: selection`. Even read-only references are forbidden — they make the leak path one careless edit away.

In SNP-tree, `selected_calls.csv` was written before label joins, `selected_calls_evaluated.csv` after — the two-file convention is the right shape, but it relies on developers never reading the labels in the selection script. The lint enforces that structurally.

Flag (R) in any file with `stage: selection`:

```r
df[["legacy_branch2_clone"]]
df$cell_type
df %>% pull(treatment)
labels$diagnosis[i]
```

Flag (Python):

```python
adata.obs["diagnosis"]
metadata["treatment"]
df.loc[:, "is_gt"]
```

Hard-fail. If the file genuinely needs labels (e.g., a sanity check gated off in production), split it into two files and tag the labels-using file `stage: evaluation`.

### 34. Output CSV with both label and score columns

Pattern: a dataframe that combines label columns and computed-score columns is written to disk. Future scripts that read the CSV inherit the leakage risk, and downstream merges become "one careless edit away" from leakage (cluster B5, 3/8 reviews).

In SNP-tree, `module_summary`, `cell_scores`, and `recursive_module_probe_selected_calls_evaluated.csv` had `legacy_branch2_clone` co-resident with discovery scores. The two-file split was the prescribed remediation; the lint catches re-regression.

Flag (R):

```r
out <- data.frame(snp_id, score, legacy_branch2_clone, ari)   # mixes labels and scores
write.csv(out, "selected_calls.csv")
```

Flag (Python):

```python
out = pd.concat([scores_df, labels_df], axis=1)
out.to_csv("selected_calls.csv")
```

Linter sketch:

1. Build the set of label columns from `analysis_labels.yml` (plus synonyms).
2. Build a set of score-like column names from project convention (`score`, `confidence`, `lr`, `posterior`, `precision`, `recall`, `ari`, `nmi`, `delta_*`, `*_score`, `*_lr`).
3. For each `write.csv` / `write_csv` / `to_csv` call, statically infer the dataframe's columns — at least where the dataframe is constructed via literal `data.frame(...)` / `pd.DataFrame({...})` / `cbind(...)` / `merge(...)`.
4. Flag when the column set intersects both label and score names, in a selection-stage file.

Allowed in evaluation-stage files with a waiver naming the file's stage explicitly:

```r
# ANALYSIS_OK[label-co-residence]: this is the evaluation-stage CSV; selection-stage
# output was selected_calls.csv (labels-free); see HANDOFF.md §2.
out <- merge(selected_calls, labels, by = "cell_id")
write.csv(out, "selected_calls_evaluated.csv")
```

### 35. Selection inputs read from labelled diagnostic outputs

Pattern: a selection-stage file `read.csv("...")` reads a file whose name flags it as a labelled diagnostic — `*_gt_*`, `*_recall_*`, `*_oracle_*`, `*_label_*`, `*_truth_*`, `*_evaluated_*`. Even if the script only uses one column, the inputs were chosen using labels (cluster A1, 6/8 reviews — the dominant analysis-side finding).

In SNP-tree, a recurring shape was: a band parameter tuned to maximize labelled recall, then reused in a "no-circularity" variant. Variant 2's claim of "no circularity" rested on band parameters being data-driven, but those parameters were themselves selected on labels.

Linter sketch:

1. Build a glob-list of label-tainted file-name patterns from project config (defaults above; extend per-project).
2. For each `read.csv` / `read.table` / `fread` / `read_csv` / `pd.read_csv` in a selection-stage file, match the path against the patterns.
3. Flag.

Hard-fail in selection-stage files. Allowed only with a waiver that demonstrates the column read is genuinely label-independent:

```r
# ANALYSIS_OK[oracle-file-read]: only the snp_id column is used from gt_recall_sweep.csv;
# this is a label-free pass-through to anchor the panel for downstream comparison.
# Verified: this script never references the gt_recall, gt_precision, or is_gt columns.
panel <- read.csv("gt_recall_sweep.csv")$snp_id
```

### 36. Thresholds and bands defined adjacent to label reads

Pattern: a constant assigned in a script whose value was demonstrably derived from a labelled summary — either because the constant is initialised from a label-tainted CSV, or because the constant is defined in a code region (within N lines) that also references label columns. Even when the *current* line doesn't touch labels, the constant carries the upstream label dependence.

This is the load-bearing pattern behind cluster A1 / A2 — the "five tightenings later, the final rule selects the c1-like module" cascade and the load-bearing VAF band whose width was chosen on labels.

Flag (R):

```r
BAND <- c(0.22, 0.36)                            # value chosen by maximizing GT-recall
sweep <- read.csv("gt17_band_sweep.csv")          # ← label-tainted upstream
BAND <- sweep[which.max(sweep$gt_recall), c("lo", "hi")]
```

Linter sketch:

1. Find constant assignments (uppercase names, function-signature defaults, top-level literal values).
2. Check whether the assignment is in a code region (±N lines) of a label-tainted CSV read or a label-column reference.
3. Flag.

The remediation declares the constant once in a config file with provenance:

```yaml
# analysis_constants.yml
band:
  lo: 0.22
  hi: 0.36
  provenance: gt17_band_sweep.csv (chosen by max GT-recall, 2026-04-15)
  is_label_tuned: true
  allowed_stages: [evaluation]   # forbid in selection
```

When `is_label_tuned: true`, the linter rejects any reference to `band` in selection-stage files.

### 37. Composite score with literal weights ≥ 3 terms

Pattern: `score = w1*x1 + w2*x2 + w3*x3 + ...` with literal numeric weights. Each weight is a choice; with three or more weights, the provenance question scales.

In SNP-tree, "eight composite scores, hand-tuned weights, post-hoc winner-picking on the same 30 SNPs" was a top finding (cluster A2). The lineage-like score had weights reverse-engineered from the X17-vs-X1 contrast on labelled data, then frozen and re-run on the same data.

Flag (R):

```r
score <- 0.30 * a + 0.40 * b + 0.20 * c + 0.10 * d
score <- a + 2 * b + 0.5 * c     # implicit weight 1 on `a`; still 3 terms
```

Flag (Python):

```python
score = 0.30 * a + 0.40 * b + 0.20 * c + 0.10 * d
```

Linter sketch: parse expressions whose top-level operator is `+`; count literal-coefficient terms; flag at ≥3.

Allowed with a waiver that cites weight-provenance and a sensitivity check:

```r
# ANALYSIS_OK[composite-weights]: weights pre-declared in decisions_pre_run.md before
# any labelled scoring run; sensitivity in composite_weight_sensitivity.R shows
# ranking unchanged for weights in [w_i +/- 0.1].
score <- 0.30 * a + 0.40 * b + 0.20 * c + 0.10 * d
```

### 38. Symmetric "best of either side" reporting

Pattern: `max(metric_target_side, metric_rest_side)` / `pmax(c1_aligned, c1_complement)` / `which.max(c(left, right))`. A blind split is symmetric — target and rest are interchangeable — but reporting the best of the two against a label is a one-bit label-aware selection.

In SNP-tree, "Symmetric 'best c1-enriched side' reporting is label-aware test multiplication" was flagged in the 2026-05-18 EM-tree review. The fix is to pre-declare which side is the target side via a label-independent rule (e.g., majority alt-bit, lower mean panel coverage) and freeze the orientation before label joins.

Flag (R):

```r
best <- pmax(target_side_ari, rest_side_ari)
which.max(c(target_c1, rest_c1))
best_side <- if (target_c1 > rest_c1) "target" else "rest"
```

Flag (Python):

```python
best = max(target_side_ari, rest_side_ari)
np.maximum(target_c1, rest_c1)
best_side = "target" if target_c1 > rest_c1 else "rest"
```

Allowed with structured waiver:

```r
# ANALYSIS_OK[symmetric-best]: side polarity pre-declared via mean panel alt-bit;
# orientation frozen before label join.
best <- if (target_alt_mean < rest_alt_mean) target_metric else rest_metric
```

### 39. Recursive calls with constant hyperparameters across depth

Pattern: a function `f(node, gates, ...)` that calls itself or a sibling `f(child, gates, ...)` with the same `gates` value. The gates were probably tuned at the root; if they're inherited at every depth, each child node is being evaluated with parent-tuned parameters.

In SNP-tree, the recursive probe hardcoded A191-tuned `BAND`, `MIN_SELECT_MODULE_SIZE`, `MIN_SELECT_BOOTSTRAP_RECURRENCE`, `MIN_SELECT_CALL_STABILITY`, and `MAX_SELECT_ASSIGNED_FRACTION` at every child node (cluster B1 at depth). The labelled-tuned parent gates became smuggled defaults at depth, and the resulting null was framed as evidence of no further structure.

Linter sketch:

1. Find recursive functions (functions that call themselves directly or via a sibling).
2. For each recursive call, check whether any hyperparameter argument is passed through unchanged from the enclosing scope.
3. Flag.

Allowed with structured waiver:

```r
# ANALYSIS_OK[constant-gates-at-depth]: gates intentionally inherited; per-node gate
# tuning would be label-leaky. Stopping rule (assigned fraction + post-selection
# enrichment vs label-shuffle null) is applied independently per node.
recurse(child, gates = gates, ...)
```

The remediation is usually a per-node gate-selection step that is itself label-free (e.g., gates chosen via OOB cell stability on the parent's blind selection).

### 40. The "no-circularity" / "blind" name antipattern

Pattern: a function or file whose name *asserts* label independence (`*_no_circularity_*`, `*_independent_*`, `*_blind_*`, `*_unsupervised_*`, `*_label_free_*`, `*_honest_*`) but whose body references label columns from `analysis_labels.yml`. The name asserts a property the code can't deliver.

In SNP-tree, multiple "Fully unsupervised" and "Honest endpoint" framings appeared in code and prose while the underlying selectors were trained on labelled c1 modules. Cluster A4 — over-framing of negative results as stopping points.

Lexical-mismatch lint: if the file or function name contains any of the assertion strings above, and the body references any column declared in `analysis_labels.yml`, flag.

Hard-fail in selection-stage files. In evaluation-stage files, allowed with a waiver:

```r
# ANALYSIS_OK[blind-name]: this function is named *_blind_evaluation_* because the
# selection it audits was blind; the function itself joins labels for the audit
# (evaluation stage).
evaluate_blind_selection_against_labels <- function(selected_calls, labels) { ... }
```

The strong remediation is to rename: a function that joins labels should be `evaluate_*` or `audit_*`, never `*_blind_*`.

## Severity levels

A useful severity model:

### Hard fail unless explicitly configured

- Broad exception handling in data loading.
- Fallback to old, backup, previous, or synthetic data.
- Random synthetic data generation in main analysis.
- Label terms in blind computation stages.
- Positional sample alignment without ID assertions.
- Silent sample dropping.

### Requires structured comment or helper

- Filtering.
- Missingness handling.
- Joins.
- Positional access.
- File selection by glob/latest/mtime.
- Caching.
- Warning suppression.
- Stochastic methods.
- Normalization and batch correction.

### Warnings or review-only initially

- Suspicious variable names.
- Report-like numbers in comments.
- Generic scientific terms in exploratory notebooks.

## Implementation sketch

Two separate linters are needed: one for Python and one for R. They share the structured-waiver mechanism, the `analysis_labels.yml` / `analysis_identifiers.yml` declarations, the stage configuration, and the severity model, but the pattern detectors are language-specific. The Python scanner can start with regex and graduate to `ast`; the R scanner can start with regex and graduate to `parse(..., keep.source = TRUE)` or `treesitter-r`. Rules that are inherently R-specific are tagged "R-specific" in the rule definitions (notably 20, 29, 30; rule 22 needs an R-aware caller-context analysis to be useful).

A first version can be intentionally simple:

```python
# tools/code_scientific_lint.py

from pathlib import Path
import re
import sys

PATTERNS = {
    "broad exception": r"except\s*(Exception)?\s*:",
    "silent pass": r"except[\s\S]{0,120}\bpass\b",
    "dropna": r"\.dropna\s*\(",
    "fillna": r"\.fillna\s*\(",
    "coerce numeric": r"to_numeric\s*\([^)]*errors\s*=\s*['\"]coerce",
    "merge without review": r"\.merge\s*\(",
    "positional iloc": r"\.iloc\s*\[",
    "fallback language": r"\b(fallback|backup|old_|previous|latest|default)\b",
    "randomness": r"\b(np\.random|numpy\.random|default_rng|rng\.|random\.)",
}

OK_MARKER = re.compile(r"ANALYSIS_OK\[[^\]]+\]:")

def nearby_has_ok_marker(lines, line_no, window=4):
    nearby = "\n".join(lines[max(0, line_no - window): line_no + window + 1])
    return bool(OK_MARKER.search(nearby))

def main():
    failed = False

    for path in Path(".").rglob("*.py"):
        if any(part in {".venv", "build", "__pycache__"} for part in path.parts):
            continue

        text = path.read_text(errors="ignore")
        lines = text.splitlines()

        for label, pattern in PATTERNS.items():
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                line_no = text[:match.start()].count("\n")
                if nearby_has_ok_marker(lines, line_no):
                    continue
                print(f"{path}:{line_no + 1}: suspicious {label}: {lines[line_no].strip()}")
                failed = True

    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
```

This is crude, but high-value. It can later become stage-aware, AST-aware, language-aware, and integrated with `analysis_labels.yml`.

## Reference architecture: R linter

A reference architecture for the R-side companion linter, sized to match the rules in this document. The Python linter follows the same shape using `ast` and a project-walk orchestrator.

### Toolchain

Build on **`lintr` + `xmlparsedata` + `xml2`**:

- `lintr` provides the per-file `Linter()` factory, `.lintr` config, RStudio/CI integration, and source-expression caching.
- `xmlparsedata` parses R code to an XML tree (this is what `lintr` uses internally).
- `xml2` runs XPath queries over the tree.

Skip these for v1: `treesitter` (faster but the API churn outweighs the benefit on a research-sized repo), `flir` (newer, less stable), writing a parser ourselves. Reach for treesitter-r only if `lint_project()` exceeds a few seconds on a real codebase.

Regex alone is a non-starter for most rules. Even rule 30 (silent `tryCatch`) needs to know that the `error =` handler body is a literal returning a non-condition value — an AST property.

### Per-file vs cross-file split

The most important architectural decision: **`lintr::Linter()` is per-file**, but about half the rules are cross-file. The package exposes two engines:

1. **`lint_file(path)`** — wraps `lintr::lint(path, linters = per_file_linters())` for the per-file rule set. Each rule is a `Linter()` factory.
2. **`lint_project(root)`** — walks every `.R` file once, builds a project index (function defs, `source()` edges, `write.csv` column sets, `read.csv` paths, stage tags from config), then runs the cross-file rules against the index. The per-file engine runs on each file during the same walk.

Per-file rules: R021, R023, R024, R027, R029, R030, R031, R032, R033, R037, R038, R040.

Cross-file rules: R020 (shadow-overwrite), R025 (def drift), R026 (dead code), R034 (label+score CSV co-residence — when df is constructed via cross-file merge), R035 (label-tainted read with project-side glob match), R036 (threshold near label read), R039 (constant gates across recursive calls).

Both engines emit a unified finding record (`file, line, rule_id, severity, message, suggested_fix, waiver_status`) — same schema as the Python linter, so downstream tooling (CI reporters, agent prompts) is shared across languages.

### Package layout

```
scilintr/
├── DESCRIPTION                  # Imports: lintr, xml2, xmlparsedata, yaml, cli, jsonlite
├── NAMESPACE
├── R/
│   ├── finding.R                # Finding record + sink (text / json / sarif)
│   ├── waiver.R                 # ANALYSIS_OK[category]: parser + nearby-comment match
│   ├── config.R                 # analysis_labels.yml, analysis_identifiers.yml, stages
│   ├── lint.R                   # lint_file() and lint_project() entry points
│   ├── per_file_linters.R       # registry of Linter() factories
│   ├── cross_file_rules.R       # registry of project-index rules
│   ├── project_index.R          # builds project-wide index once per run
│   └── cli.R                    # main() — Rscript entry point
├── inst/
│   ├── bin/scilintr             # thin shell wrapper around Rscript -e
│   └── extdata/default-config/  # example analysis_labels.yml etc.
├── tests/testthat/
│   ├── fixtures/
│   │   └── R<NN>_<slug>/
│   │       ├── bad_<case>.R     # carries: # EXPECTED: R<NN> at line <N>
│   │       └── good_<case>.R
│   ├── helper-fixtures.R        # parse_expected(), expect_finding helpers
│   └── test-fixtures.R          # generic fixture-walking test driver
└── README.md
```

Downstream projects install via `remotes::install_github("user/scilintr")`, drop `analysis_labels.yml` and `.scilintr.yml` at the project root, and add `scilintr` to `make quick-check`.

### TDD with testthat

Fixture-driven, one rule at a time. The contract is **encoded in the fixture file itself** — bad files carry `# EXPECTED: R<NN> at line <N>` headers; good files carry no expectations. A single `test-fixtures.R` walks every fixture directory and asserts:

- For each `bad_*.R`: every expected finding is produced (rule and line match).
- For each `good_*.R`: no findings of the directory's rule fire.

Adding a new bad case for an existing rule is a one-file addition (`bad_<case>.R` with the EXPECTED header). The fixture itself is the test; the rule implementation is the code that makes the test pass.

For each rule, the bad fixtures should be **real or minimally-reduced failure cases from this repo and other projects**, not invented examples. That keeps the test set anchored to genuine failure modes.

The TDD loop:

1. Add `bad_<case>.R` (with EXPECTED header) and `good_<case>.R` to `tests/fixtures/R<NN>_<slug>/`.
2. Run `devtools::test()` → fails: bad case produces no finding because the rule is unimplemented.
3. Implement the rule in `R/per_file_linters.R` (or `R/cross_file_rules.R`).
4. Run `devtools::test()` → green.
5. Add more bad cases as edge cases surface in agent runs.

### Worked example: per-file rule (R030)

```r
silent_trycatch_linter <- function() {
  lintr::Linter(function(source_expression) {
    xml <- source_expression$full_xml_parsed_content
    if (is.null(xml)) return(list())

    # tryCatch(..., error = function(e) <literal>)
    handlers <- xml2::xml_find_all(
      xml,
      "//SYMBOL_FUNCTION_CALL[text()='tryCatch']/parent::expr/following-sibling::SYMBOL_SUB[text()='error']/following-sibling::expr[1]"
    )
    bad <- Filter(function(h) {
      body <- xml2::xml_find_first(h, ".//expr[last()]")
      tag  <- xml2::xml_name(xml2::xml_child(body, 1))
      tag %in% c("NUM_CONST", "NULL_CONST", "STR_CONST")
    }, handlers)

    lapply(bad, function(node) {
      lintr::Lint(
        filename    = source_expression$filename,
        line_number = as.integer(xml2::xml_attr(node, "line1")),
        type        = "warning",
        message     = "R030: tryCatch swallows error and returns a literal — log explicitly or rethrow.",
        linter      = "silent_trycatch_linter"
      )
    })
  })
}
```

### Worked example: cross-file rule (R020 shadow-overwrite)

```r
# Phase 1: project index (built once per lint_project run)
build_project_index <- function(files) {
  list(
    defs    = collect_fn_defs(files),       # data.frame: name, file, line
    sources = collect_source_edges(files),  # data.frame: file, sourced_file
    writes  = collect_write_calls(files),
    reads   = collect_read_calls(files),
    stage   = stage_for_file(files)
  )
}

# Phase 2: rule
rule_R020_shadow_overwrite <- function(idx) {
  shadowed <- merge(idx$sources, idx$defs,
                    by.x = "sourced_file", by.y = "file") |>
    merge(idx$defs, by.x = c("file", "name"), by.y = c("file", "name"))
  emit_findings(shadowed, "R020",
                "function redefined locally after source() — shadows the library version")
}
```

### R-specific gotchas baked in

- **All assignment operators**: `<-`, `=`, `->`, `<<-`, `assign()`. Top-level-function-definition queries must catch all of them.
- **Roxygen comments**: `xmlparsedata` retains them as `COMMENT` nodes. Strip them when scanning for `ANALYSIS_OK[...]` near a finding, otherwise an unrelated roxygen tag can spoof a waiver.
- **`source(..., local = TRUE)`**: changes scope semantics. The shadow-overwrite rule should only flag `local = FALSE` (the default).
- **S3/S4 dispatch, `do.call`, `get(name)()`**: false positives in rule R026 (dead code). Gate strict-mode behind a flag; treat the warning as advisory by default.
- **Alternative imports**: `pacman::p_load`, `box::use`, `import::from`, `library()`. The `source()`-edge collector should know about these. For v1, handle `source()` and `sys.source()` only; add the others as edge cases.

### What you don't need yet

- A language server (lintr's CLI output is enough for `make quick-check` and agent loops).
- An AST diff / autofix layer (suggested-fix strings in the finding record are enough until rule accuracy is validated).
- treesitter-r (reconsider only if `lint_project()` exceeds a few seconds on a real codebase).
- Per-rule fine-grained severity beyond `warning` / `error` (the existing severity model in this document is enough for v1).

## Recommended starting rules

Start with the ten highest-value checks:

1. No raw positional metadata/sample indexing.
2. No label terms in blind stages.
3. No broad exceptions or fallback data loading.
4. No random synthetic data generation in main analysis.
5. No joins without cardinality checks.
6. No sample filtering or dropping without a ledger or structured comment.
7. No missingness coercion or imputation without a structured comment.
8. No magic thresholds in analysis filters.
9. No stochastic methods without seeds.
10. No cache reuse without input fingerprints.

For R-flavored analysis projects, add these five (from rules 20, 22, 24, 29, 30):

11. No `source(...)` followed by redefinition of a sourced name (shadow-overwrite).
12. No `set.seed(...)` inside a function body, unless the function is the per-task entry point for parallel work.
13. No scientifically meaningful function-signature default in library code — name it, declare it in config, or add a structured waiver.
14. No `read.csv(...)` without `check.names = FALSE` when the script references column names containing `-`, `>`, `:`, or starting with a digit.
15. No `tryCatch(..., error = function(e) <value>)` that swallows the error and returns a numerically-valid stand-in — log explicitly or rethrow.

For projects with selection/evaluation stage separation, add these five leakage rules (from rules 32, 33, 34, 35, 40):

16. No tie-break on a label or GT column anywhere; hard-fail in selection-stage files.
17. No label-column reference (read or write) in selection-stage files.
18. No selection-stage CSV that co-resides label columns and score columns.
19. No selection-stage read of files whose names match label-tainted patterns (`*_gt_*`, `*_oracle_*`, `*_truth_*`, `*_evaluated_*`).
20. No `*_blind_*` / `*_no_circularity_*` / `*_unsupervised_*` naming on code that references label columns.

These catch many agent failure modes while keeping the system lightweight.

## Operating model

The lint strategy is meant to be cheap and frequent.

Recommended workflow:

```text
1. Agent edits analysis code.
2. Agent runs make quick-check.
3. Linter flags suspicious code.
4. Agent either removes the pattern, names it, adds an assertion/ledger, or adds a structured waiver.
5. Human or review agent inspects the structured waivers.
```

The linter does not need to be perfect. Its job is to make hidden scientific commitments visible early.

