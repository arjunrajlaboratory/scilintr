"""Rule: hardcoded-design-formula — model formulas or contrasts as string/tuple literals."""

from __future__ import annotations

RULE = "hardcoded-design-formula"

BAD_FORMULA = """
formula = "~ treatment + batch"
"""

BAD_CONTRAST = """
contrast = ("treatment", "treated", "control")
"""

GOOD = """
import yaml
config = yaml.safe_load(open("de_model.yml"))
formula = config["formula"]
"""

WAIVED = """
# ANALYSIS_OK[contrast-definition]: locked model per project decision; mirrored in outputs/de_model.yml
formula = "~ treatment + batch"
"""


def test_hardcoded_design_formula_flags_formula(has_finding):
    assert has_finding(BAD_FORMULA, RULE)


def test_hardcoded_design_formula_flags_contrast(has_finding):
    assert has_finding(BAD_CONTRAST, RULE)


def test_hardcoded_design_formula_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_hardcoded_design_formula_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
