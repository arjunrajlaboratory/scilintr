"""unchecked-cache — ``if <output>.exists(): return read_csv(<output>)`` without input fingerprint."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unchecked-cache"
MESSAGE = (
    "returning a cached output based only on `.exists()` — compare input fingerprints "
    "(mtime, content hash, or an explicit cache-is-valid helper) or add ANALYSIS_OK[cache]"
)


_KNOWN_READERS = {
    "read_csv",
    "read_parquet",
    "read_table",
    "read_pickle",
    "read_hdf",
    "read_feather",
    "read_json",
    "read_orc",
    "read_excel",
    "read_h5ad",
    "load",
    "load_cached",
    "open_zarr",
    "loadtxt",
    "loadmat",
}


def _is_exists_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "exists"
    )


def _return_reads_cached(body: list[ast.stmt], cached_name: str) -> bool:
    """``cached_name`` is the Name whose ``.exists()`` was checked. We require either
    a direct ``return <cached_name>`` or a known reader call that takes the cached name.
    Calls to functions like ``.thread()`` / ``.spread()`` no longer slip through.
    """
    if not body:
        return False
    first = body[0]
    if not isinstance(first, ast.Return) or first.value is None:
        return False
    val = first.value

    if isinstance(val, ast.Name) and val.id == cached_name:
        return True

    if isinstance(val, ast.Call):
        # Reader call with the cached name as an argument.
        if isinstance(val.func, ast.Attribute) and val.func.attr in _KNOWN_READERS:
            for arg in val.args:
                if isinstance(arg, ast.Name) and arg.id == cached_name:
                    return True
        # Bare reader name like `read_csv(cached_name)`.
        if isinstance(val.func, ast.Name) and val.func.id in _KNOWN_READERS:
            for arg in val.args:
                if isinstance(arg, ast.Name) and arg.id == cached_name:
                    return True
    return False


def _cached_name_from_exists(test: ast.AST) -> str | None:
    # test is `<X>.exists()` — extract X if it's a Name.
    if not _is_exists_call(test):
        return None
    func = test.func  # type: ignore[attr-defined]
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return func.value.id
    return None


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if not _is_exists_call(node.test):
            continue
        cached_name = _cached_name_from_exists(node.test)
        if cached_name is None:
            # We can't tie the exists() check to a specific variable, so the
            # "is this the cached path being read?" question is unanswerable.
            # Don't flag — avoids the dict-subscript exists() false positive.
            continue
        if not _return_reads_cached(node.body, cached_name):
            continue
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
