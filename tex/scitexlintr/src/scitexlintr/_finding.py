from dataclasses import dataclass
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Finding:
    rule: str
    line: int
    col: int
    message: str
    severity: Severity
    filename: str = ""
    # snapshot-mismatch carries the suggested replacement so --write can rewrite.
    fix: "Fix | None" = None


@dataclass(frozen=True)
class Fix:
    """Byte-offset replacement for --write mode."""
    start: int
    end: int
    replacement: str
