"""Regressions from the documentation-coherence review."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scitexlintr import lint_tex, parse_manifest
from scitexlintr.cli import main as cli_main

SRC = Path(__file__).resolve().parents[1] / "src" / "scitexlintr"


def test_fail_on_error_ignores_warnings_for_the_exit_code(tmp_path):
    report = tmp_path / "r.html"
    report.write_text("<!doctype html><html><body><p>We saw 999 cells.</p></body></html>", encoding="utf-8")
    assert cli_main([str(report)]) == 1                      # default: any finding fails
    assert cli_main([str(report), "--fail-on=error"]) == 0   # warnings alone do not
    report.write_text('<!doctype html><html><body><p><span data-sci-val="x">1</span></p></body></html>', encoding="utf-8")
    manifest = tmp_path / "m.json"
    manifest.write_text('{"numbers": []}', encoding="utf-8")
    assert cli_main([str(report), f"--manifest={manifest}", "--fail-on=error"]) == 1  # unknown-value-id is an error


def test_tex_hint_for_a_rendered_value_uses_the_stored_snapshot():
    m = parse_manifest({"numbers": [{"id": "frac", "value": 0.9535, "unit": "percent", "precision": 1}]})
    (finding,) = [f for f in lint_tex("We kept 95.4\\% of claims.", manifest=m) if f.rule == "raw-generated-value"]
    assert "\\SciVal{\\Frac}{0.9535}" in finding.message
    fixed = "We kept \\SciVal{\\Frac}{0.9535} of claims."
    assert [f.rule for f in lint_tex(fixed, manifest=m)] == []


def test_every_module_compiles_without_warnings():
    for path in SRC.rglob("*.py"):
        proc = subprocess.run([sys.executable, "-W", "error", "-c", f"compile(open({str(path)!r}).read(), {str(path)!r}, 'exec')"],
                              capture_output=True, text=True)
        assert proc.returncode == 0, (path.name, proc.stderr[-300:])
