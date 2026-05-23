"""Tests for explicit UTF-8 encoding on every file read.

Path.read_text() with no encoding uses locale.getpreferredencoding(False),
which is cp1252 on default Windows installs. A manifest or .tex file
containing UTF-8 bytes (µ, Å, Greek, etc.) silently mojibakes or raises
on those systems. We assert the fix by intercepting Path.read_text and
checking the encoding kwarg.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from scitexlintr import lint_file, load_manifest


def test_load_manifest_reads_utf8(tmp_path: Path):
    """Self-review bug: Path.read_text() without encoding mojibakes UTF-8
    on cp1252-default systems."""
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(
        json.dumps(
            {"numbers": [{"id": "alpha", "value": 0.05,
                          "label_canonical": "α-threshold (µ adjusted)"}]}
        ).encode("utf-8")
    )
    captured_kwargs: dict = {}
    real_read_text = Path.read_text

    def spy(self, *args, **kwargs):
        captured_kwargs.update(kwargs)
        return real_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", spy):
        m = load_manifest(manifest_path)

    assert captured_kwargs.get("encoding") == "utf-8", (
        f"load_manifest must pass encoding='utf-8' to read_text; got {captured_kwargs}"
    )
    assert "α" in m.numbers[0].label_canonical


def test_lint_file_reads_utf8(tmp_path: Path):
    src_path = tmp_path / "report.tex"
    src_path.write_bytes(
        "\\begin{document}\nWith p = 0.05 (α threshold)\n\\end{document}\n".encode("utf-8")
    )
    captured_kwargs: dict = {}
    real_read_text = Path.read_text

    def spy(self, *args, **kwargs):
        captured_kwargs.update(kwargs)
        return real_read_text(self, *args, **kwargs)

    with patch.object(Path, "read_text", spy):
        lint_file(src_path)

    assert captured_kwargs.get("encoding") == "utf-8"
