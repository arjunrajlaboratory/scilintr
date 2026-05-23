"""CLI entry point — scaffold."""
from __future__ import annotations

import sys

from .lint import lint_project


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = args[0] if args else "."
    findings = lint_project(root)
    if not findings:
        print("scilintr: no findings")
        return 0
    for f in findings:
        print(f.format())
    print(f"scilintr: {len(findings)} finding(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
