# scilintr (Python)

The Python flavor of [scilintr](../../README.md). Same rule set (R001–R040),
same spec, same waiver mechanism — implemented with `ast` instead of
`xml2`/XPath.

**Status: scaffold.** The package layout is in place but rule implementations
are not yet written. See the [R package](../../r/scilintr/) for the canonical
working implementation; the Python flavor will mirror its architecture.

## Planned layout

```
py/scilintr/
├── pyproject.toml
├── src/scilintr/
│   ├── __init__.py
│   ├── finding.py            # Finding dataclass + JSON sink
│   ├── waiver.py             # ANALYSIS_OK[category]: matcher
│   ├── stage.py              # # STAGE: <name> header detection
│   ├── constants.py          # TRIVIAL_LITERALS allowlist
│   ├── config.py             # YAML config loader
│   ├── lint.py               # lint_file / lint_project entry points
│   ├── project_index.py      # cross-file index (function defs, sources, etc.)
│   ├── per_file_linters.py   # registry of per-file rules
│   ├── cross_file_rules.py   # registry of project-level rules
│   ├── rules/
│   │   ├── r001_positional_access.py
│   │   ├── r002_magic_threshold.py
│   │   └── ...
│   └── cli.py
└── tests/
    ├── fixtures/             # same R<NN>_<slug>/ shape as r/scilintr/
    └── test_fixtures.py      # generic fixture-walking driver
```

The Python rule implementations will use `ast.NodeVisitor` subclasses
instead of XPath. Same finding-record schema, same `ANALYSIS_OK[...]`
waiver categories.

## Development

```bash
cd py/scilintr
pip install -e ".[dev]"
pytest
```
