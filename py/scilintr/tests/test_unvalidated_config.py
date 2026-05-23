"""Rule: unvalidated-config — ``yaml.safe_load`` / ``json.load`` result accessed via ``.get`` instead of being passed through a schema.

A loader that accepts any keys silently drops typos (e.g. ``bach_size: 32`` →
no such key → falls back to the hard-coded default) and doesn't enforce bounds
on continuous parameters. Schema validation catches both classes at boundary
crossing time instead of as silent downstream weirdness.
"""

from __future__ import annotations

RULE = "unvalidated-config"

BAD_YAML = """
import yaml

with open("config.yml") as f:
    config = yaml.safe_load(f)

threshold = config.get("fdr", 0.05)
batch_size = config.get("batch_size", 32)
"""

BAD_JSON = """
import json

with open("config.json") as f:
    config = json.load(f)

threshold = config.get("fdr", 0.05)
"""

GOOD = """
import yaml
from pydantic import BaseModel, Field

class Config(BaseModel, extra="forbid"):
    fdr: float = Field(0.05, gt=0, lt=1)
    batch_size: int = Field(32, ge=1)

with open("config.yml") as f:
    raw = yaml.safe_load(f)
config = Config.model_validate(raw)
threshold = config.fdr
"""

WAIVED = """
import yaml

# ANALYSIS_OK[unvalidated-config]: dev sandbox loader; production loader in build/cli.py validates
with open("config.yml") as f:
    config = yaml.safe_load(f)

threshold = config.get("fdr", 0.05)
"""


def test_unvalidated_config_flags_yaml(has_finding):
    assert has_finding(BAD_YAML, RULE)


def test_unvalidated_config_flags_json(has_finding):
    assert has_finding(BAD_JSON, RULE)


def test_unvalidated_config_passes_good_code(has_finding):
    assert not has_finding(GOOD, RULE)


def test_unvalidated_config_respects_waiver(has_finding):
    assert not has_finding(WAIVED, RULE)
