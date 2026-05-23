"""Detect ``# ANALYSIS_OK[category]: explanation`` waiver comments.

A well-formed waiver requires three things:

1. The ``ANALYSIS_OK`` token.
2. A category in square brackets, drawn from the project's vocabulary
   (any ``[\\w-]+`` for now — strict mapping can be opted in later).
3. A colon followed by a non-empty explanation.

Anything else (``# ANALYSIS_OK``, ``# ANALYSIS_OK[cat]``, ``# ANALYSIS_OK[cat]:``)
is rejected. The structure exists to force a reviewable statement, not to wave off
arbitrary code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WAIVER_RE = re.compile(
    r"#\s*ANALYSIS_OK\[(?P<category>[\w-]+)\]:\s*(?P<explanation>\S.*?)\s*$"
)

DEFAULT_WINDOW = 4


@dataclass(frozen=True)
class Waiver:
    line: int
    category: str
    explanation: str


def find_waivers(source: str) -> list[Waiver]:
    waivers: list[Waiver] = []
    for line_no, line in enumerate(source.splitlines(), start=1):
        m = _WAIVER_RE.search(line)
        if m:
            waivers.append(
                Waiver(
                    line=line_no,
                    category=m.group("category"),
                    explanation=m.group("explanation"),
                )
            )
    return waivers


def is_waived(finding_line: int, waivers: list[Waiver], window: int = DEFAULT_WINDOW) -> bool:
    # Waivers are forward-looking: a waiver on line L suppresses findings on lines [L, L+window].
    # Same-line covers inline trailing comments (`except Exception:  # ANALYSIS_OK[...]: ...`).
    return any(0 <= finding_line - w.line <= window for w in waivers)
