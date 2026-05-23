"""Rule protocol.

* ``Rule`` — per-file check. Most rules fit here.
* ``CrossFileRule`` — multi-file check. Sees the full parsed set at once.
  Used when the dangerous pattern only emerges when sibling files diverge
  (e.g., a constant in one file disagrees with a CLI default in another).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Callable

from scilintr._finding import Finding

CheckFn = Callable[[ast.AST, str, str], list[Finding]]
# (filename -> (tree, source)) -> list[Finding]
CrossFileCheckFn = Callable[[dict[str, tuple[ast.AST, str]]], list[Finding]]


@dataclass(frozen=True)
class Rule:
    code: str
    check: CheckFn


@dataclass(frozen=True)
class CrossFileRule:
    code: str
    check_files: CrossFileCheckFn
