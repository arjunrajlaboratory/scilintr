"""Minimal command-line interface — point at files or directories, get findings.

Usage:

    python -m scilintr <path> [<path>...]
    python -m scilintr --rules broad-exception,unchecked-merge <path>
    python -m scilintr --no-waivers <path>   # audit mode

Exit code is 1 if any findings are produced, 0 otherwise.

Pointing at a directory enables cross-file rules (e.g.,
``duplicate-parameter-source`` detects a constant in one file disagreeing
with a CLI default in another).
"""

from __future__ import annotations

import argparse
import sys

from scilintr import lint_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint Python for hidden scientific commitments")
    parser.add_argument("paths", nargs="+", help="files or directories to lint")
    parser.add_argument(
        "--rules",
        type=str,
        default=None,
        help="comma-separated rule codes to restrict to (default: all rules)",
    )
    parser.add_argument(
        "--no-waivers",
        action="store_true",
        help="ignore ANALYSIS_OK waivers (audit mode)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print only a per-rule count summary, not individual findings",
    )
    args = parser.parse_args(argv)

    rules = [r.strip() for r in args.rules.split(",")] if args.rules else None

    findings = lint_paths(
        args.paths,
        rules=rules,
        respect_waivers=not args.no_waivers,
    )

    if args.summary:
        by_rule: dict[str, int] = {}
        for f in findings:
            by_rule[f.rule] = by_rule.get(f.rule, 0) + 1
        for rule_code, count in sorted(by_rule.items(), key=lambda kv: -kv[1]):
            print(f"{count:>5}  {rule_code}")
        print(f"{len(findings):>5}  TOTAL")
    else:
        for f in findings:
            print(f"{f.filename}:{f.line}:{f.col}: [{f.rule}] {f.message}")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
