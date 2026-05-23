"""hardcoded-sample-ids — list of sample-ID-shaped strings assigned to an exclusion-named variable."""

from __future__ import annotations

import ast
import re

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "hardcoded-sample-ids"
MESSAGE = (
    "sample IDs hard-coded in source — load from a ledger (build/dropped_samples.tsv) or "
    "add ANALYSIS_OK[sample-exclusion] explaining why these specific samples are excluded"
)

_EXCLUSION_NAME_RE = re.compile(r"(exclud|drop|bad|outlier|remov|skip)", re.IGNORECASE)
_SAMPLE_ID_RE = re.compile(r"^(S|sample[_-]?|sub[_-]?|donor[_-]?|p)\d+$", re.IGNORECASE)


def _is_sample_id_list(value: ast.AST) -> bool:
    if not isinstance(value, ast.List):
        return False
    if len(value.elts) < 2:
        return False
    str_consts = [e for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
    if len(str_consts) != len(value.elts):
        return False
    return all(_SAMPLE_ID_RE.match(c.value) for c in str_consts)


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not _is_sample_id_list(node.value):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and _EXCLUSION_NAME_RE.search(target.id):
                findings.append(
                    Finding(
                        rule=CODE,
                        line=node.lineno,
                        col=node.col_offset,
                        message=MESSAGE,
                        severity="structured-comment",
                    )
                )
                break
    return findings


rule = Rule(code=CODE, check=_check)
