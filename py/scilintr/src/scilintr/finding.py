"""Finding record — shared schema with the R package."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Severity = Literal["warning", "error", "style"]


@dataclass(frozen=True)
class Finding:
    """One lint finding.

    Fields match `scilintr_finding` in the R package so downstream
    tooling (CI reporters, agent prompts) sees the same schema.
    """

    file: str
    line: int
    rule: str          # e.g. "R030"
    message: str
    severity: Severity = "warning"
    suggested_fix: str | None = None
    waiver_status: str = "none"

    def format(self) -> str:
        return f"{self.file}:{self.line} [{self.rule}/{self.severity}] {self.message}"
