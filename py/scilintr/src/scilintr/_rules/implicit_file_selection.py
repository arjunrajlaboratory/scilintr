"""implicit-file-selection — globs + sort/mtime tricks, ``latest``/``backup``/``old`` in path literals."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "implicit-file-selection"
MESSAGE = (
    "implicit file selection (glob-and-sort, latest/backup/old literal) — pin a specific "
    "release identifier or add ANALYSIS_OK[file-selection] with fingerprint check"
)

_SUSPICIOUS_TOKENS = (
    "latest",
    "old",
    "backup",
    "previous",
    "tmp",
    "temp",
    "copy",
    "archive",
    "final_final",
)

# Only treat a string as a file path when it ends with a known data/config extension.
# This filters out docstring prose like "previously duplicated" or "latest release".
_DATA_EXTENSIONS = (
    ".csv",
    ".tsv",
    ".h5ad",
    ".h5",
    ".hdf5",
    ".parquet",
    ".feather",
    ".pickle",
    ".pkl",
    ".npz",
    ".npy",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
    ".gz",
    ".zip",
    ".mtx",
    ".loom",
    ".zarr",
)


def _string_has_suspicious_token(value: str) -> bool:
    low = value.lower()
    return any(token in low for token in _SUSPICIOUS_TOKENS)


def _looks_path_like(value: str) -> bool:
    """A heuristic for `is this string actually a file path` to filter out prose."""
    low = value.lower()
    return any(low.endswith(ext) for ext in _DATA_EXTENSIONS)


def _is_glob_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "glob":
        return True
    if isinstance(func, ast.Name) and func.id == "glob":
        return True
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    glob_lines: set[int] = set()

    for node in ast.walk(tree):
        if _is_glob_call(node):
            glob_lines.add(node.lineno)
            findings.append(
                Finding(
                    rule=CODE,
                    line=node.lineno,
                    col=node.col_offset,
                    message=MESSAGE,
                    severity="structured-comment",
                )
            )
            continue
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and _string_has_suspicious_token(node.value)
            and _looks_path_like(node.value)
            and node.lineno not in glob_lines
        ):
            findings.append(
                Finding(
                    rule=CODE,
                    line=node.lineno,
                    col=node.col_offset,
                    message=MESSAGE,
                    severity="structured-comment",
                )
            )

    return findings


rule = Rule(code=CODE, check=_check)
