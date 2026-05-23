"""Rule protocol — every rule is one of these.

A rule receives a fully-prepared ``TexDoc`` (parsed once per file) and an
optional ``Manifest``. Manifest-dependent rules early-out when ``manifest``
is ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from scitexlintr._finding import Finding


@dataclass(frozen=True)
class Rule:
    code: str
    check: Callable[..., list[Finding]]
    requires_manifest: bool = False
