"""synthetic-data-generation — random distribution result assigned to a data-like name.

Triggers when ``np.random.<dist>(...)`` (or any ``rng.<dist>(...)``) appears as the
value of an assignment to a variable that *looks like* a data matrix or labels
container. ``rng.permutation(...)`` assigned to ``permutation`` is fine — the same
call assigned to ``labels`` is not.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "synthetic-data-generation"
MESSAGE = (
    "synthetic random data assigned to a data-like variable — forbidden in main analysis; "
    "add ANALYSIS_OK[simulation-only] / [canary-corruption] / [synthetic-test-fixture] if intentional"
)

# Distribution-y names: anything that yields numbers shaped like real data.
_GENERATIVE = {
    "poisson",
    "normal",
    "uniform",
    "exponential",
    "gamma",
    "binomial",
    "multinomial",
    "lognormal",
    "negative_binomial",
    "beta",
    "chisquare",
    "geometric",
    "standard_normal",
}

_DATA_LIKE_NAMES = {
    "counts",
    "expr",
    "expression",
    "data",
    "X",
    "y",
    "Y",
    "adata",
    "df",
    "labels",
    "metadata",
    "samples",
    "features",
    "counts_df",
    "expr_df",
    "matrix",
}


def _is_generative_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    # np.random.<dist>(...) or numpy.random.<dist>(...) or rng.<dist>(...)
    if isinstance(func, ast.Attribute) and func.attr in _GENERATIVE:
        return True
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not _is_generative_call(node.value):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in _DATA_LIKE_NAMES:
                findings.append(
                    Finding(
                        rule=CODE,
                        line=node.lineno,
                        col=node.col_offset,
                        message=MESSAGE,
                        severity="hard-fail",
                    )
                )
                break
    return findings


rule = Rule(code=CODE, check=_check)
