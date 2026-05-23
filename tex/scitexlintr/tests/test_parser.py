"""Tests for the TeX scanner — comments, math, balanced braces, body extraction."""

from __future__ import annotations

from scitexlintr._parser import (
    find_body_range,
    find_macro_calls,
    strip_comments,
)


def test_strip_comments_removes_to_end_of_line():
    src = "Hello % comment\nWorld\n"
    out = strip_comments(src)
    assert out[:7] == "Hello  "
    assert "comment" not in out
    assert out.count("\n") == 2


def test_strip_comments_preserves_offsets():
    src = "abc % junk\ndef\n"
    out = strip_comments(src)
    assert len(out) == len(src)
    # ``def`` retains its original offset.
    assert out.index("def") == src.index("def")


def test_strip_comments_respects_escaped_percent():
    src = r"Recovered 50\% of reads % real comment"
    out = strip_comments(src)
    # The escaped percent stays as ``\%``; the real comment is blanked.
    assert "50\\%" in out
    assert "real comment" not in out


def test_strip_comments_preserves_inline_verb():
    """Self-review bug: '%' inside \\verb|...| was treated as a comment,
    blanking the verb's closing delimiter and corrupting downstream offsets."""
    src = r"Coverage = \verb|x = 50%| at most, see notes."
    out = strip_comments(src)
    assert r"\verb|x = 50%|" in out, (
        f"verb body was eaten by comment stripping; got {out!r}"
    )


def test_strip_comments_preserves_verbatim_environment():
    src = "Some prose.\n\\begin{verbatim}\nrate = 0.05 % comment-like\n\\end{verbatim}\nMore prose."
    out = strip_comments(src)
    assert "rate = 0.05 % comment-like" in out


def test_strip_comments_double_backslash_is_not_an_escape():
    # ``\\%`` -> two backslashes followed by %, where the % IS a comment.
    src = r"line ends \\% comment-here"
    out = strip_comments(src)
    assert "comment-here" not in out


def test_find_body_range_skips_preamble():
    src = (
        "\\documentclass{article}\n"
        "\\newcommand{\\Foo}{1}\n"
        "\\begin{document}\n"
        "Body text.\n"
        "\\end{document}\n"
    )
    start, end = find_body_range(src)
    body = src[start:end]
    assert "Body text" in body
    assert "documentclass" not in body
    assert "end{document}" not in body


def test_find_macro_calls_balances_braces():
    src = r"\SciVal{\NSamples}{48} \emph{nested {braces} here}"
    calls = find_macro_calls(src, names={"SciVal", "emph"})
    by_name = {c.name: c for c in calls}
    assert "SciVal" in by_name
    assert by_name["SciVal"].args[0].text == r"\NSamples"
    assert by_name["SciVal"].args[1].text == "48"
    assert by_name["emph"].args[0].text == "nested {braces} here"


def test_find_macro_calls_handles_optional_args():
    src = r"\includegraphics[width=0.6\textwidth]{figures/qc.png}"
    calls = find_macro_calls(src, names={"includegraphics"})
    assert len(calls) == 1
    call = calls[0]
    assert call.optional_args[0].text == r"width=0.6\textwidth"
    assert call.args[0].text == "figures/qc.png"


def test_find_macro_calls_ignores_unmatched():
    src = r"\SciVal{\NSamples}{47} and \\\foo unrelated"
    calls = find_macro_calls(src, names={"SciVal"})
    assert len(calls) == 1


def test_find_macro_calls_handles_newline_between_args():
    """Self-review bug: _skip_whitespace only skipped ' '/'\\t', dropping
    the second arg when authors wrap macros across lines."""
    src = "\\SciVal{\\NSamples}\n    {47}"
    calls = find_macro_calls(src, names={"SciVal"})
    assert len(calls) == 1
    assert len(calls[0].args) == 2, (
        f"newline-separated arg dropped; got {len(calls[0].args)} args"
    )
    assert calls[0].args[1].text == "47"


def test_find_macro_calls_handles_newline_before_first_arg():
    src = "\\section\n{Results}"
    calls = find_macro_calls(src, names={"section"})
    assert len(calls) == 1 and len(calls[0].args) == 1
    assert calls[0].args[0].text == "Results"
