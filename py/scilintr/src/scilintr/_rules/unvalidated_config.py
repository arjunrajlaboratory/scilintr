"""unvalidated-config — yaml.safe_load / json.load result accessed via .get/subscript without a schema.

Tracks variables whose value is produced by ``yaml.safe_load(...)`` or ``json.load(...)``.
If that variable is later read via ``.get(...)`` or subscript access, flag — the
typo/bounds vulnerabilities described in the strategy doc apply. If the variable
is instead passed to a validator call (any function returning a typed object),
no finding fires.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "unvalidated-config"
MESSAGE = (
    "config loaded without schema validation — typos silently dropped, bounds unchecked; "
    "validate with pydantic/dataclass (extra='forbid') or add ANALYSIS_OK[unvalidated-config]"
)


def _is_loader_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr == "safe_load" and isinstance(func.value, ast.Name) and func.value.id in {"yaml"}:
        return True
    if func.attr == "load" and isinstance(func.value, ast.Name) and func.value.id in {"yaml", "json"}:
        return True
    return False


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    loaded_vars: dict[str, int] = {}  # name -> lineno of assignment
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_loader_call(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    loaded_vars[target.id] = node.lineno

    if not loaded_vars:
        return []

    findings: list[Finding] = []
    flagged_lines: set[int] = set()
    for name, assign_line in loaded_vars.items():
        for node in ast.walk(tree):
            # .get(key, default) call on the loaded var
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == name
            ):
                if assign_line not in flagged_lines:
                    flagged_lines.add(assign_line)
                    findings.append(
                        Finding(
                            rule=CODE,
                            line=assign_line,
                            col=0,
                            message=MESSAGE,
                            severity="structured-comment",
                        )
                    )
                break
            # Subscript access on the loaded var: `config["fdr"]`
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == name
            ):
                if assign_line not in flagged_lines:
                    flagged_lines.add(assign_line)
                    findings.append(
                        Finding(
                            rule=CODE,
                            line=assign_line,
                            col=0,
                            message=MESSAGE,
                            severity="structured-comment",
                        )
                    )
                break

    return findings


rule = Rule(code=CODE, check=_check)
