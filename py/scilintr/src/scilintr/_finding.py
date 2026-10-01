from dataclasses import dataclass
from typing import Literal

Severity = Literal["hard-fail", "structured-comment", "warning"]


@dataclass(frozen=True)
class Finding:
    rule: str
    line: int
    col: int
    message: str
    severity: Severity
    # Filename is populated by the engine; rules don't need to set it themselves.
    # Default is "" for backward compatibility with rules that construct findings
    # without knowing the filename (the engine attaches it after).
    filename: str = ""
    # Last line of the flagged statement's header, when it spans several
    # (a multi-line ``with (...)``). A waiver from ``window`` lines above
    # ``line`` through ``waiver_end`` applies; ``None`` means just ``line``.
    waiver_end: int | None = None
