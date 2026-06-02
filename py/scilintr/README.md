# scilintr (Python)

AST-based linter for hidden scientific commitments in Python data-analysis
code. Sibling of [`r/scilintr/`](../../r/scilintr/) (R code) and
[`tex/scitexlintr/`](../../tex/scitexlintr/) (LaTeX reports); same waiver
mechanism (`# ANALYSIS_OK[category]: explanation`, ``% ANALYSIS_OK[...]:``
for the TeX linter), same agent-first design philosophy (high recall
over precision).

## Rules

Each rule has a kebab-case code that names the failure mode. Rules currently
implemented:

| Code | What it flags |
|---|---|
| `broad-exception` | `except Exception:` without re-raise — silent error swallowing |
| `silent-pass` | `except ...: pass` (any exception type) |
| `return-none-on-missing-input` | `if not path.exists(): return None` |
| `positional-metadata-access` | `df.iloc[:, 3]` for metadata columns |
| `magic-threshold` | Bare numeric thresholds in DataFrame filters (`padj < 0.05`); `> 0` / `>= 0` natural floors are exempt |
| `unchecked-merge` | `pd.merge(...)` with no `validate=` or row-count assert |
| `positional-sample-alignment` | Aligning two DataFrames by row order, not key |
| `unannotated-filter` | `df = df[df.col > X]` with no length/count log |
| `unannotated-missingness` | `df.dropna()` / `df.fillna()` with no missingness audit |
| `implicit-file-selection` | `glob.glob("*.csv")[0]` — order-dependent file pick |
| `unchecked-cache` | Reading a cache file without checking when it was written |
| `synthetic-data-generation` | Synthetic data created with no documented purpose |
| `unseeded-stochastic` | `np.random.*` without a documented seed |
| `label-in-blind-stage` | Label-tainted reads in a `# STAGE: selection` file |
| `hardcoded-design-formula` | `formula = "~ condition"` literal in analysis code |
| `unannotated-transform` | `np.log2(x + 1)` / `np.clip(...)` with no rationale |
| `ambiguous-layer-access` | `adata.X` without an explicit `layer=` |
| `hardcoded-sample-ids` | Sample IDs as literals (`if sample == "S123"`) |
| `warning-suppression` | `warnings.filterwarnings("ignore")` |
| `unchecked-model-fit` | `.fit()` returns ignored — no convergence / fit-quality check |
| `plot-side-effect-filter` | Plot code that mutates the DataFrame in place |
| `unconsumed-cli-flag` | `parser.add_argument(...)` whose dest is never read |
| `duplicate-parameter-source` | Same param declared in two places (per file) |
| `duplicate-parameter-source` (cross-file) | Constant in one file disagreeing with CLI default in another, scoped to a shared directory |
| `runtime-assert` | `assert` in production code (stripped by `-O`) |
| `unvalidated-config` | Config dict read without a schema check |
| `sentinel-mask-assignment` | `df.loc[mask, col] = -999` style sentinel writes |

See [`../../analysis_lint_strategy.md`](../../analysis_lint_strategy.md) for
the design rationale and [`../../docs/failure-modes.md`](../../docs/failure-modes.md)
for the bugs each rule catches.

## Install / use

```bash
cd py/scilintr
pip install -e ".[dev]"

# lint a file or directory
scilintr path/to/analysis/
scilintr --rules broad-exception,unchecked-merge path/to/file.py
scilintr --no-waivers path/to/file.py     # audit mode: ignore ANALYSIS_OK
scilintr --summary path/to/dir/           # per-rule counts only
```

Exit code is `1` if any findings are produced, `0` otherwise.

## API

```python
from scilintr import lint_code, lint_paths, Finding

findings = lint_code(source_string, filename="foo.py")
findings = lint_paths(["path/to/dir/", "path/to/file.py"])

# Restrict to a subset of rules
findings = lint_code(src, rules=["broad-exception", "unchecked-merge"])

# Audit mode — surface waivered findings too
findings = lint_code(src, respect_waivers=False)
```

`Finding` is a frozen dataclass: `rule`, `line`, `col`, `message`,
`severity` (`"hard-fail" | "structured-comment" | "warning"`), `filename`.

## Waivers

A finding can be suppressed by a structured comment on (or up to four lines
before) the offending line:

```python
# ANALYSIS_OK[api-retry]: external API requires bare Exception
try:
    response = client.fetch()
except Exception:
    retry()
```

The square-bracket category is required and free-form (`[\w-]+`). The
colon-and-explanation is required and must be non-empty — the structure
exists to force a reviewable statement, not to wave off arbitrary code.

## Development

```bash
cd py/scilintr
pip install -e ".[dev]"
pytest                              # full suite
pytest tests/test_broad_exception.py    # iterate on one rule
```

Each rule has three tests:

- `test_<rule>_flags_bad_code` — bad code produces ≥1 finding for the rule
- `test_<rule>_passes_good_code` — equivalent good code produces zero findings
- `test_<rule>_respects_waiver` — `# ANALYSIS_OK[<category>]:` suppresses

The waiver test only becomes meaningful once the rule detects the pattern;
before then it passes vacuously. That's the natural TDD inflection inside
each rule: implement detection → bad-code test passes → add waiver
suppression → all three pass.
