"""Diff — governance comparison between stages."""

from __future__ import annotations

from ussy_seral.models import GovernancePrescription, Stage
from ussy_seral.prescribe import governance_diff, prescribe, get_builtin_rules


def diff_stages(from_stage: Stage, to_stage: Stage) -> dict:
    """Compare governance rules between two stages.

    Returns a dict with 'added', 'removed', and 'changed' lists of strings.
    """
    return governance_diff(from_stage, to_stage)


def diff_prescriptions(
    from_stage: Stage, to_stage: Stage, path: str = ""
) -> dict:
    """Generate full governance diff with prescriptions for both stages.

    Returns a dict with from_prescription, to_prescription, and changes.
    """
    from_prescription = prescribe(from_stage, path)
    to_prescription = prescribe(to_stage, path)
    changes = diff_stages(from_stage, to_stage)

    return {
        "from": from_prescription.to_dict(),
        "to": to_prescription.to_dict(),
        "changes": changes,
    }
