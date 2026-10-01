"""End-to-end test: run scitexlintr against tests/data/report.tex and verify
that every ``% LINT-EXPECT[rule-a,rule-b]`` marker fires its listed rules
on the next line, and every ``% LINT-OK`` marker has no findings on the
next line.

Markers must live on a line by themselves. The "next line" is the next
non-blank, non-comment line — that lets us add a blank line between
marker and target for readability if needed.
"""

from __future__ import annotations

import re

import pytest

from scitexlintr import lint_html, lint_tex

# TeX markers are ``% ...`` comment lines; HTML markers are single-line
# ``<!-- ... -->`` comments. Both corpora share one checker so the two
# frontends are held to the same marker semantics.
_SYNTAX = {
    "tex": (
        re.compile(r"^\s*%\s*LINT-EXPECT\[(?P<rules>[^\]]+)\]\s*$"),
        re.compile(r"^\s*%\s*LINT-OK\s*$"),
        re.compile(r"^\s*%"),
    ),
    "html": (
        re.compile(r"^\s*<!--\s*LINT-EXPECT\[(?P<rules>[^\]]+)\]\s*-->\s*$"),
        re.compile(r"^\s*<!--\s*LINT-OK\s*-->\s*$"),
        re.compile(r"^\s*<!--.*-->\s*$"),
    ),
}
_EXPECT_RE, _OK_RE, _COMMENT_RE = _SYNTAX["tex"]
_BLANK_RE = re.compile(r"^\s*$")


def _next_code_line(lines: list[str], from_idx: int, comment_re=None) -> int:
    """Return the 1-indexed line number of the next non-comment, non-blank line."""
    comment_re = comment_re or _COMMENT_RE
    for j in range(from_idx, len(lines)):
        line = lines[j]
        if _BLANK_RE.match(line):
            continue
        if comment_re.match(line):
            continue
        return j + 1
    raise AssertionError(f"no code line after index {from_idx}")


def test_corpus_matches_markers(corpus_source, corpus_manifest):
    findings = lint_tex(corpus_source, filename="report.tex", manifest=corpus_manifest)
    _check_markers(corpus_source, findings, "tex")


def test_html_corpus_matches_markers(html_corpus_source, corpus_manifest):
    findings = lint_html(html_corpus_source, filename="report.html", manifest=corpus_manifest)
    _check_markers(html_corpus_source, findings, "html")


def test_html_corpus_exercises_every_html_rule(html_corpus_source, corpus_manifest):
    findings = lint_html(html_corpus_source, filename="report.html", manifest=corpus_manifest)
    fired = {f.rule for f in findings}
    expected = {
        "snapshot-mismatch", "raw-generated-value", "unwrapped-threshold",
        "unfingerprinted-figure", "unsourced-numeric-token",
        "overloaded-term-no-warning", "forbidden-alias",
        "handwritten-numeric-claim", "magic-tex-threshold",
        "unknown-value-id", "unfingerprinted-data", "script-data-literal",
    }
    assert not expected - fired, f"HTML corpus does not exercise: {sorted(expected - fired)}"


def _check_markers(corpus_source: str, findings, fmt: str) -> None:
    expect_re, ok_re, comment_re = _SYNTAX[fmt]
    findings_by_line: dict[int, set[str]] = {}
    for f in findings:
        findings_by_line.setdefault(f.line, set()).add(f.rule)

    lines = corpus_source.splitlines()
    failures: list[str] = []
    seen_markers = 0

    for i, line in enumerate(lines):
        expect = expect_re.match(line)
        ok = ok_re.match(line)
        if not expect and not ok:
            continue
        seen_markers += 1
        target_line = _next_code_line(lines, i + 1, comment_re)
        fired = findings_by_line.get(target_line, set())

        if expect:
            wanted = {r.strip() for r in expect.group("rules").split(",")}
            missing = wanted - fired
            extra = fired - wanted
            if missing:
                failures.append(
                    f"line {i + 1} marker LINT-EXPECT[{','.join(sorted(wanted))}] "
                    f"-> target line {target_line}: missing rules {sorted(missing)}; "
                    f"fired={sorted(fired)}"
                )
            if extra:
                # Strict exclusivity: a LINT-EXPECT line must declare every
                # rule that fires. Declare overlapping rules explicitly so
                # silent extra firings (which would mean a regression in
                # one rule's heuristics) become visible.
                failures.append(
                    f"line {i + 1} marker LINT-EXPECT[{','.join(sorted(wanted))}] "
                    f"-> target line {target_line}: extra unexpected rules "
                    f"{sorted(extra)}; declare them in the marker if intended"
                )
        elif ok:
            if fired:
                failures.append(
                    f"line {i + 1} marker LINT-OK -> target line {target_line}: "
                    f"unexpected findings {sorted(fired)}"
                )

    assert seen_markers > 0, "corpus has no LINT-EXPECT / LINT-OK markers"
    if failures:
        pytest.fail("\n".join(failures))


def test_corpus_exercises_every_rule(corpus_source, corpus_manifest):
    """Make sure the corpus actually fires every rule at least once.

    A safety net so future edits don't silently drop coverage of a rule.
    """
    findings = lint_tex(corpus_source, filename="report.tex", manifest=corpus_manifest)
    fired_rules = {f.rule for f in findings}
    expected = {
        "snapshot-mismatch",
        "raw-generated-value",
        "bare-generated-macro",
        "unwrapped-threshold",
        "unfingerprinted-figure",
        "unsourced-numeric-token",
        "overloaded-term-no-warning",
        "forbidden-alias",
        "handwritten-numeric-claim",
        "magic-tex-threshold",
    }
    missing = expected - fired_rules
    assert not missing, f"corpus does not exercise rules: {sorted(missing)}"


def test_corpus_waiver_suppresses_handwritten_claim(corpus_source, corpus_manifest):
    """The waivered line ``N = 23`` must NOT produce a handwritten-numeric-claim."""
    findings = lint_tex(corpus_source, filename="report.tex", manifest=corpus_manifest)
    # Find the line of the body `We mentioned N = 23 cells in passing,`
    target_line = None
    for i, line in enumerate(corpus_source.splitlines(), start=1):
        if "We mentioned N = 23" in line:
            target_line = i
            break
    assert target_line is not None
    fired = {f.rule for f in findings if f.line == target_line}
    assert "handwritten-numeric-claim" not in fired, (
        f"waiver did not suppress handwritten-numeric-claim on line {target_line}; "
        f"fired={fired}"
    )


def test_corpus_audit_mode_resurrects_waivered_finding(corpus_source, corpus_manifest):
    """With ``respect_waivers=False`` the suppressed finding comes back."""
    findings = lint_tex(
        corpus_source,
        filename="report.tex",
        manifest=corpus_manifest,
        respect_waivers=False,
    )
    target_line = None
    for i, line in enumerate(corpus_source.splitlines(), start=1):
        if "We mentioned N = 23" in line:
            target_line = i
            break
    assert target_line is not None
    fired = {f.rule for f in findings if f.line == target_line}
    assert "handwritten-numeric-claim" in fired
