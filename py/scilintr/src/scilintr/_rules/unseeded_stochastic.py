"""unseeded-stochastic — known stochastic method without a ``random_state``/``seed`` kwarg."""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unseeded-stochastic"
MESSAGE = (
    "stochastic method invoked without a seed — results will vary run-to-run; "
    "pass random_state=SEED or add ANALYSIS_OK[random-seed-only]"
)

_STOCHASTIC_NAMES = {
    "KMeans",
    "KNeighborsClassifier",
    "KNeighborsRegressor",
    "MiniBatchKMeans",
    "DBSCAN",
    "AgglomerativeClustering",
    "GaussianMixture",
    "UMAP",
    "TSNE",
    "train_test_split",
    "StratifiedKFold",
    "KFold",
    "RandomForestClassifier",
    "RandomForestRegressor",
    "GradientBoostingClassifier",
    "GradientBoostingRegressor",
    "LogisticRegression",
    "MLPClassifier",
    "MLPRegressor",
}

_SEED_KWARGS = {"random_state", "seed", "rng"}


def _called_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _has_seed_kwarg(node: ast.Call) -> bool:
    return any(kw.arg in _SEED_KWARGS for kw in node.keywords)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _called_name(node)
        if name not in _STOCHASTIC_NAMES:
            continue
        if _has_seed_kwarg(node):
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
