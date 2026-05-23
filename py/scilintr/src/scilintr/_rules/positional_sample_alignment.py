"""positional-sample-alignment — assigning ``df.columns`` (or ``.index``) from another frame's column.

The canonical bad shape is ``counts.columns = metadata['sample_id']`` — sample identity
is inferred by row order rather than verified via an explicit join.
"""

from __future__ import annotations

import ast

from scilintr._finding import Finding
from scilintr._rules._base import Rule

CODE = "positional-sample-alignment"
MESSAGE = (
    "assigning `.columns`/`.index` from another frame's column relies on row order — "
    "use df.loc[:, other['ids']] and assert column equality, or add ANALYSIS_OK[id-alignment]"
)

_LABEL_ATTRS = {"columns", "index"}

# Slice keys that strongly suggest the RHS is a *sample identifier column* from
# another DataFrame — those are the patterns the rule actually cares about. A
# generic key like ``"new_columns"`` or a self-attribute like ``self.column_names``
# is almost certainly a name list, not a cross-frame Series.
_SAMPLE_ID_KEYS = frozenset(
    {
        "sample_id",
        "sampleid",
        "sample",
        "barcode",
        "barcodes",
        "cell_id",
        "cellid",
        "donor_id",
        "donor",
        "subject_id",
        "subject",
        "patient_id",
        "id",
    }
)


def _rhs_pulls_from_other_frame(value: ast.AST) -> bool:
    """RHS looks like a cross-frame *sample-identifier column*.

    Triggered by ``other_df["sample_id"]`` and similar — not by generic dict
    subscript like ``config["new_columns"]`` or ``self.column_names``.
    """
    if not isinstance(value, ast.Subscript):
        return False
    if not isinstance(value.value, ast.Name):
        return False
    slc = value.slice
    if not (isinstance(slc, ast.Constant) and isinstance(slc.value, str)):
        return False
    return slc.value.lower() in _SAMPLE_ID_KEYS


def _check(tree: ast.AST, source: str, filename: str) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr in _LABEL_ATTRS
                and _rhs_pulls_from_other_frame(node.value)
            ):
                findings.append(
                    Finding(
                        rule=CODE,
                        line=node.lineno,
                        col=node.col_offset,
                        message=MESSAGE,
                        severity="hard-fail",
                    )
                )
                break
    return findings


rule = Rule(code=CODE, check=_check)
