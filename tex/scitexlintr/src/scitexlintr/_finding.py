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
    """Byte-offset replacement for --write mode.

    ``replaces_markup`` marks an HTML fix whose replacement is authored markup
    (a manifest ``display_html`` with tags); only such a fix may overwrite a
    region that already contains markup."""
    start: int
    end: int
    replacement: str
    replaces_markup: bool = False
