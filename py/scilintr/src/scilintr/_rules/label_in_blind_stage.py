"""label-in-blind-stage — experimental-label references in files identified as blind stages.

The stage is inferred from the filename. Tokens that mark a file as blind: ``blind``,
``qc``, ``pca``, ``umap``, ``tsne``, ``hvg``, ``cluster``, ``embedding``, ``neighbors``,
``normalize``, ``variable_gene``. (Project config can override this later.)

In blind files, the rule flags subscript access whose key is a known label term
(``treatment``, ``condition``, ``response``, ...) and ``df.query("group == ...")``
calls that mention label terms.
"""

from __future__ import annotations

import ast
import os
import re

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "label-in-blind-stage"
MESSAGE = (
    "experimental-label column referenced in a blind-stage file — labels must not influence "
    "unsupervised computation; defer the join until after coordinates are fixed or add "
    "ANALYSIS_OK[label-annotation-only]"
)

_BLIND_TOKENS = frozenset(
    {
        "blind",
        "qc",
        "pca",
        "umap",
        "tsne",
        "hvg",
        "cluster",
        "embedding",
        "neighbors",
        "normalize",
        "variable_gene",
    }
)

_LABEL_TERMS = {
    "treatment",
    "condition",
    "phenotype",
    "diagnosis",
    "response",
    "outcome",
    "case",
    "control",
    "treated",
    "responder",
    "contrast",
    "label",
    "class",
    "group",
}

_QUERY_LABEL_RE = re.compile(r"\b(" + "|".join(_LABEL_TERMS) + r")\b")


def _is_blind_file(filename: str) -> bool:
    base = os.path.basename(filename).lower()
    if base.endswith(".py"):
        base = base[:-3]
    # Tokenize on common separators so substrings like "hvg" inside "shvg" don't fire.
    parts = re.split(r"[_\-.]", base)
    return any(part in _BLIND_TOKENS for part in parts if part)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    if not _is_blind_file(filename):
        return []

    findings: list[Finding] = []
    for node in ast.walk(tree):
        # Subscript with a string-constant key that is a label term.
        if isinstance(node, ast.Subscript):
            slc = node.slice
            if isinstance(slc, ast.Constant) and isinstance(slc.value, str) and slc.value in _LABEL_TERMS:
                findings.append(
                    Finding(
                        rule=CODE,
                        line=node.lineno,
                        col=node.col_offset,
                        message=MESSAGE,
                        severity="hard-fail",
                    )
                )
                continue
        # .query("group == 'treated'") with label term in the expression.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "query"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and _QUERY_LABEL_RE.search(node.args[0].value)
        ):
            findings.append(
                Finding(
                    rule=CODE,
                    line=node.lineno,
                    col=node.col_offset,
                    message=MESSAGE,
                    severity="hard-fail",
                )
            )

    return findings


rule = Rule(code=CODE, check=_check)
