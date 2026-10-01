"""Command-line entry point — point at a .tex file (and optionally a manifest)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scitexlintr import __version__
from scitexlintr._engine import apply_fixes, format_for_path, lint_file
from scitexlintr._macros import defined_macros_in_file
from scitexlintr._manifest import load_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scitexlintr",
        description="Lint LaTeX and HTML reports for scientific drift",
    )
    parser.add_argument("--version", action="version", version=f"scitexlintr {__version__}")
    parser.add_argument("paths", nargs="+", help=".tex or .html report files to lint")
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="path to manifest.json (enables manifest-dependent rules)",
    )
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
        "--write",
        action="store_true",
        help="auto-fix snapshot-mismatch findings in place (HTML: rewrites rendered values)",
    )
    parser.add_argument(
        "--fail-on",
        choices=("any", "error"),
        default="any",
        help="exit 1 on any remaining finding (default) or only on error-severity findings",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="print only a per-rule count summary",
    )
    args = parser.parse_args(argv)

    rules = [r.strip() for r in args.rules.split(",")] if args.rules else None

    # A multi-file report defines macros in one file and uses them in another
    # (main.tex's preamble, chapter1.tex's prose): pool definitions over the run.
    pooled: set[str] = set()
    for raw in args.paths:
        if Path(raw).is_file() and format_for_path(raw) == "tex":
            pooled |= defined_macros_in_file(Path(raw))

    total_findings = 0
    failing = 0
    by_rule: dict[str, int] = {}
    for raw in args.paths:
        p = Path(raw)
        if not p.is_file():
            print(f"{p}: not found", file=sys.stderr)
            return 2
        findings = lint_file(
            p,
            manifest_path=args.manifest,
            rules=rules,
            respect_waivers=not args.no_waivers,
            defined_macros=pooled,
        )
        if args.write:
            source = p.read_text(encoding="utf-8")
            new_source, n_fixed = apply_fixes(source, findings, fmt=format_for_path(p))
            if n_fixed:
                p.write_text(new_source, encoding="utf-8")
                print(f"{p}: rewrote {n_fixed} snapshot(s)", file=sys.stderr)
            # Re-lint after fixes so the report reflects remaining issues.
            findings = lint_file(
                p,
                manifest_path=args.manifest,
                rules=rules,
                respect_waivers=not args.no_waivers,
                defined_macros=pooled,
            )

        for f in findings:
            by_rule[f.rule] = by_rule.get(f.rule, 0) + 1
            if not args.summary:
                print(f"{f.filename}:{f.line}:{f.col}: [{f.rule}] {f.message}")
            total_findings += 1
            if args.fail_on == "any" or f.severity == "error":
                failing += 1

    if args.summary:
        for rule_code, count in sorted(by_rule.items(), key=lambda kv: -kv[1]):
            print(f"{count:>5}  {rule_code}")
        print(f"{total_findings:>5}  TOTAL")

    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
