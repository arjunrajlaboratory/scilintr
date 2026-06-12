# scitexlintr — Scientific Linting for LaTeX Reports

Catches numeric drift, raw values, unverified figures, and unsourced claims
in `.tex` source. Companion to [scilintr](../../README.md), which lints
analysis code (Python/R).

```text
scilintr     →  scientific commitments in analysis CODE
scitexlintr  →  scientific commitments in REPORTS
```

## Why this exists

Reports drift from the analysis that produced them. A number gets copied
into the `.tex` source and then becomes stale when the data or code
changes. A figure gets regenerated but the prose still describes the old
version. A threshold gets relaxed in code but stays at the old value in
the abstract. A contrast phrase ("treated versus control") gets reversed
in the analysis config but the text never gets updated.

These are not LaTeX bugs. They are **silent scientific drift**. ChkTeX,
lacheck, TeXtidote, and Vale won't catch them — they check typography,
grammar, and prose style, not whether the numbers in the prose match the
analysis that produced them.

scitexlintr is the linter for that layer:

> Numbers, thresholds, figures, and short phrases in a scientific report
> must be traceable to a checked source.

Combined with a small **manifest** (a JSON file enumerating the report's
reportable values), and a tiny **wrapper convention** (`\SciVal` and
`\SciText`), the linter can detect drift the moment it happens.

## The wrapper convention

Two LaTeX macros, defined once per report:

```latex
\newcommand{\SciVal}[2]{#1}    % numeric values
\newcommand{\SciText}[2]{#1}   % text values
```

Both take two arguments and render only the first. The second is a
human-readable snapshot for review.

Usage in prose:

```latex
We analyzed \SciVal{\NSamples}{48} samples at FDR $< \SciVal{\FDRThreshold}{0.05}$.

For the contrast \SciText{\ContrastPhrase}{treated versus control},
\SciVal{\NDEGenesFDR}{317} genes were differentially expressed.
```

`\NSamples`, `\FDRThreshold`, etc. are generated macros emitted from the
manifest. The PDF prints only their expansion — fresh by construction.
The snapshot (`48`, `0.05`, `317`) is what the source file shows for
review.

scitexlintr checks that **every snapshot equals the macro's current
expansion**. Drift = lint error.

## The manifest

scitexlintr expects a manifest JSON file describing the reportable
artifacts. **This schema is scitexlintr's published contract** — any
project that emits it can use the linter.

### Minimal schema

```json
{
  "numbers": [
    {
      "id": "n_samples",
      "value": 48,
      "label_canonical": "number of cells passing QC",
      "label_aliases_forbidden": ["total cells", "total barcodes"]
    }
  ],
  "figures": [
    {
      "id": "volcano_de",
      "path": "outputs/figures/volcano_de.pdf",
      "sha256": "b4e3c9d2..."
    }
  ],
  "terms": [
    {
      "id": "BCLRT",
      "expansion": "branch-coherency log-likelihood ratio test",
      "overloaded_warning": "Not a Wilks-sense LRT; threshold 10 corresponds to Wilks 20."
    }
  ]
}
```

All top-level keys are optional — pass only what you need. Extra fields
are ignored (scitexlintr is tolerant of supersets like mycelium's
`.manifest.json`).

### Macro names from ids

scitexlintr expects generated macros to follow a deterministic CamelCase
transform of the manifest `id`:

| Manifest id | Macro name |
|---|---|
| `n_samples` | `\NSamples` |
| `fdr_threshold` | `\FDRThreshold` |
| `n_de_genes_fdr_0_05` | `\NDEGenesFDRZeroZeroFive` |
| `x17_module_c1_precision` | `\XOneSevenModuleCOnePrecision` |
| `diff-expr.n_samples` | `\NSamples` (namespace stripped) |
| `diff-expr:n_replicates` | `\NReplicates` (colon namespace also stripped) |

The transform: strip the namespace prefix (everything before the last
`.`, `:`, or `/`), split the local key on `_`, and per segment —
all-digit → English words digit-by-digit, ≤3-letter all-letter →
uppercase (acronym), otherwise title-case the letters **and spell out any
embedded digit** (`c1` → `COne`, `x17` → `XOneSeven`). Concatenate. Digits
never survive into a macro name: a LaTeX control word is letters-only, so a
bare digit would terminate the name (`\C` plus a literal `1`, not `\COne`).

The macros themselves are emitted by upstream tooling (mycelium's
`render_report_values_tex`, or any equivalent); scitexlintr does not emit
them — it only predicts their names so it can match snapshots.

## Install

```bash
pip install scitexlintr
```

Verify with `scitexlintr --help`.

## Usage

```bash
# Lint a single file against a manifest
scitexlintr report.tex --manifest=.manifest.json

# Lint without a manifest (manifest-free rules only)
scitexlintr report.tex

# Auto-fix stale snapshots
scitexlintr report.tex --manifest=.manifest.json --write

# Audit mode: show findings even where waivers exist
scitexlintr report.tex --manifest=.manifest.json --no-waivers

# Restrict to specific rules
scitexlintr report.tex --rules=snapshot-mismatch,raw-generated-value

# Per-rule count summary instead of per-finding lines
scitexlintr report.tex --manifest=.manifest.json --summary
```

Exit code is `1` if any findings remain after waivers, `0` otherwise. The
CLI lists findings as `path:line:col: [rule-code] message`.

Library API:

```python
from scitexlintr import lint_tex, lint_file, load_manifest, apply_fixes

manifest = load_manifest(".manifest.json")
findings = lint_tex(source_string, filename="report.tex", manifest=manifest)
new_source, n_applied = apply_fixes(source_string, findings)
```

## Rule catalog

### Manifest-dependent rules (require `--manifest`)

| Rule | Severity | What it catches |
|---|---|---|
| `snapshot-mismatch` | error | `\SciVal{\Macro}{stale}` where the snapshot disagrees with the manifest value. Auto-fixable with `--write` (string values are TeX-escaped before writing; fixes that would erase a TeX comment inside the snapshot brace are skipped). |
| `raw-generated-value` | error | A literal `48` or `"treated versus control"` in prose that matches a manifest value. Handles scientific notation (`1e-8` and `1e-08`) and comma-grouped integers (`15,122`). |
| `bare-generated-macro` | warning | `\NSamples` used directly in prose without a `\SciVal` wrapper — fresh but unreviewable. Skips structural-macro args (`\label`, `\ref`, `\cite`, `\input`, …) just like the prose mask does for every other rule. |
| `unwrapped-threshold` | error | `FDR < 0.05` in prose when `\FDRThreshold` exists in the manifest. Recognizes `<`, `>`, `<=`, `>=`, `\le`, `\leq`, `\ge`, `\geq`, `\ll`, `\gg`; numbers include scientific notation. |
| `unfingerprinted-figure` | error | `\includegraphics{...}` referencing a path not in `manifest.figures[*]`. Forgiving in one direction: a tex-side extensionless path (`figures/foo`) matches a manifest-side `figures/foo.pdf`. |
| `unsourced-numeric-token` | warning | Any numeric token in prose with no corresponding manifest entry. Skips structural references (`Section 4.2`, `Figure (3)`), typographic percentages (`50\%`), threshold contexts, scientific-notation tails, and tokens already accounted for by `handwritten-numeric-claim`. |
| `overloaded-term-no-warning` | warning | A term in `manifest.terms[*]` with `overloaded_warning` set, but the warning is absent both before the first use AND from the same sentence as the first use. |
| `forbidden-alias` | error | A manifest value used with one of its `label_aliases_forbidden` (e.g., calling `exact_accuracy` "accuracy"). Skips occurrences that are part of the canonical label. |

### Manifest-free rules (always on)

| Rule | Severity | What it catches |
|---|---|---|
| `handwritten-numeric-claim` | warning | Hand-typed `n = 48`, `p = 1e-8`, `r = 0.82` patterns in prose. Single-letter prefixes only — `mean = 23` does not match. |
| `magic-tex-threshold` | warning | Bare numeric thresholds in prose (`< 0.05`, `> 1.0`) without a wrapper or named macro. Includes scientific notation. |

## Waivers

scitexlintr inherits scilintr's waiver mechanism, adapted to TeX comment
syntax. A waiver is a structured one-line declaration of intent placed on
or up to four lines above the offending line:

```latex
% ANALYSIS_OK[handwritten-numeric-claim]: discussion footnote citing Bagamery 2024 N=23, not a result of this analysis
We mentioned 23 cells in passing, as in earlier work.
```

A useful waiver answers three questions:

1. **What is being done?**
2. **Why is it scientifically valid?**
3. **Where is it recorded, asserted, or checked?**

If you can't write a structured waiver honestly, the choice probably
needs to be reconsidered, not justified.

**What does not count:**

- `% ANALYSIS_OK` (no category, no explanation)
- `% ANALYSIS_OK[handwritten-claim]: fine` (vacuous)
- `% ANALYSIS_OK[junk]: shut up linter` (the structure exists to force
  thought; bypassing it is failure)

Waivers are rule-scoped: `% ANALYSIS_OK[snapshot-mismatch]: …` only
suppresses `snapshot-mismatch` on the lines it covers, not (say)
`raw-generated-value`. Inside `\verb|...|` or a `verbatim`/`lstlisting`/
`minted` environment, `%` is treated as a literal character and does
not start a comment — so a waiver-looking string inside verbatim code
is harmless.

## Integration recipes

### Makefile

```makefile
report.pdf: report.tex .manifest.json
	scitexlintr report.tex --manifest=.manifest.json
	latexmk -pdf -interaction=nonstopmode -halt-on-error report.tex
```

### CI

A glob inside ``--manifest=…`` is not shell-expanded (the whole
``--flag=value`` is one token), so multi-report trees need a loop that
pairs each report with the manifest sitting next to it:

```yaml
- name: Lint reports
  run: |
    for tex in analysis/*/reports/*.tex; do
      dir=$(dirname "$tex")
      scitexlintr "$tex" --manifest="$dir/.manifest.json"
    done
```

### Pre-commit

scitexlintr does not (yet) ship a ``.pre-commit-hooks.yaml``, so the
``repo:`` form won't install. Use the ``repo: local`` form against the
already-installed ``scitexlintr`` command:

```yaml
repos:
  - repo: local
    hooks:
      - id: scitexlintr
        name: scitexlintr
        entry: scitexlintr
        language: system
        files: \.tex$
        args: [--manifest=.manifest.json]
```

This assumes ``scitexlintr`` is on ``$PATH`` (``pip install`` it, or run
``pre-commit`` inside a venv that has it) and that ``.manifest.json``
sits alongside the staged ``.tex``. For multiple report directories,
swap ``args`` for a small wrapper script that mirrors the CI loop above.

## Relationship to other LaTeX tools

scitexlintr is complementary to existing tools — they check different
layers. Run all of them:

| Tool | Layer | Example finding |
|---|---|---|
| **ChkTeX / lacheck** | typography | `dont -> don't`, `Inter-word spacing after period`, math/text mode confusion |
| **TeXtidote** | grammar (LanguageTool over stripped prose) | subject-verb agreement, awkward phrasing |
| **Vale** | prose style / controlled vocabulary | "very" usage, banned words, style guide compliance |
| **scitexlintr** | **scientific commitments** | snapshot drift, raw generated values, unfingerprinted figures, handwritten numeric claims |

None of these overlap. ChkTeX won't tell you a number is wrong. Vale
won't tell you a figure is stale. scitexlintr won't tell you a comma is
misplaced. Use them together.

## Producing a manifest

scitexlintr does not produce manifests — it consumes them. Producers
include:

- **mycelium**: `register_value(...)` calls in analysis code emit
  fragments; the `report-generator` convention pack merges and enriches
  them into `.manifest.json`.
- **Hand-authored**: write the JSON yourself. The schema is small.
- **Your own pipeline**: any tool that can emit the schema works.

The wrapper macros (`\SciVal`, `\SciText`) and the macro names
(`\NSamples` etc.) likewise come from upstream tooling. scitexlintr only
checks consistency between the source, the wrappers, and the manifest.

## Project layout

```
tex/scitexlintr/
├── pyproject.toml
├── README.md                   <- this file
├── src/scitexlintr/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                  <- argparse entry point
│   ├── _doc.py                 <- per-file preprocessed view
│   ├── _engine.py              <- lint_tex + apply_fixes
│   ├── _finding.py             <- Finding + Fix dataclasses
│   ├── _manifest.py            <- JSON loader + id→macro transform
│   ├── _parser.py              <- TeX scanner (comments, verbatim, balanced braces, prose mask)
│   ├── _waivers.py             <- TeX-comment ANALYSIS_OK[...] detection
│   └── _rules/                 <- one file per rule
└── tests/
    ├── conftest.py             <- shared fixtures
    ├── test_<rule>.py          <- per-rule BAD/GOOD/WAIVED cases
    ├── test_corpus.py          <- end-to-end against tests/data/
    └── data/
        ├── report.tex          <- annotated `% LINT-EXPECT[rule]` / `% LINT-OK`
        └── manifest.json
```

## Development

```bash
cd tex/scitexlintr
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest             # 117 tests
.venv/bin/scitexlintr tests/data/report.tex --manifest=tests/data/manifest.json
```

The end-to-end corpus is `tests/data/report.tex` + `tests/data/manifest.json`.
Each marker comment `% LINT-EXPECT[rule,rule,...]` or `% LINT-OK` on the
line immediately above a code line documents (and asserts) what the
linter should find on that line. Strict exclusivity: a `LINT-EXPECT`
line must declare EVERY rule that fires on the next code line.

## License

MIT.
