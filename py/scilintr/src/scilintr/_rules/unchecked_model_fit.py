"""unchecked-model-fit — iterative solver ``.fit(...)`` without a convergence check.

Tracks variables assigned from known iterative-solver classes, then verifies that
after each ``.fit(...)`` call the same variable's ``n_iter_`` or ``converged_``
attribute is referenced. Convergence checks expressed as raises or asserts
involving these attributes count.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unchecked-model-fit"
MESSAGE = (
    "iterative solver `.fit()` without a follow-up convergence check — read model.n_iter_ / "
    "model.converged_ and raise on non-convergence, or add ANALYSIS_OK[model-fit]"
)

_ITERATIVE_SOLVERS = {
    "LogisticRegression",
    "MLPClassifier",
    "MLPRegressor",
    "GaussianMixture",
    "BayesianGaussianMixture",
    "ElasticNet",
    "Lasso",
    "Ridge",
    "GradientBoostingClassifier",
    "GradientBoostingRegressor",
    "LinearMixedModel",
}


def _is_iterative_solver_call(value: ast.AST) -> bool:
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    if isinstance(func, ast.Name) and func.id in _ITERATIVE_SOLVERS:
        return True
    if isinstance(func, ast.Attribute) and func.attr in _ITERATIVE_SOLVERS:
        return True
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    # Map of solver-variable name -> first assignment line
    solver_vars: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_iterative_solver_call(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    solver_vars[target.id] = node.lineno

    if not solver_vars:
        return []

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "fit"):
            continue
        if not isinstance(func.value, ast.Name) or func.value.id not in solver_vars:
            continue

        name = func.value.id
        # Check whether n_iter_/converged_ is referenced on this variable anywhere after the fit.
        fit_line = node.lineno
        has_check = False
        for other in ast.walk(tree):
            if not isinstance(other, ast.Attribute):
                continue
            if other.attr not in {"n_iter_", "converged_"}:
                continue
            if not isinstance(other.value, ast.Name) or other.value.id != name:
                continue
            if other.lineno > fit_line:
                has_check = True
                break

        if not has_check:
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
