"""Amendment Processor — Structured Revision with Germane-ness Testing."""

from __future__ import annotations

import uuid
from typing import Dict, Optional, Set

from parliament.models import Motion, MotionStatus
from parliament.motion import MotionEngine

GERMANENESS_THRESHOLD = 0.6
MAX_AMENDMENT_DEPTH = 3


def germaneness(amendment_scope: Set[str], original_scope: Set[str]) -> float:
    """Jaccard similarity of affected scopes."""
    if not amendment_scope and not original_scope:
        return 1.0
    intersection = len(amendment_scope & original_scope)
    union = len(amendment_scope | original_scope)
    return intersection / union if union > 0 else 0.0


def is_amendment_admissible(
    amendment_scope: Set[str],
    original_scope: Set[str],
    depth: int,
    threshold: float = GERMANENESS_THRESHOLD,
    max_depth: int = MAX_AMENDMENT_DEPTH,
) -> bool:
    return germaneness(amendment_scope, original_scope) >= threshold and depth <= max_depth


class AmendmentEngine:
    def __init__(self, motion_engine: MotionEngine):
        self.motion_engine = motion_engine

    def propose_amendment(
        self,
        original_motion_id: str,
        agent_id: str,
        action: str,
        scope: Optional[Set[str]] = None,
        criticality_map: Optional[Dict[str, float]] = None,
    ) -> Motion:
        original = self.motion_engine.get_motion(original_motion_id)
        if not original:
            raise ValueError(f"Original motion {original_motion_id} not found")
        if original.status != MotionStatus.FLOOR and original.status != MotionStatus.DOCKET:
            raise ValueError(f"Original motion {original_motion_id} is not open for amendment")

        depth = (original.depth or 0) + 1
        if depth > MAX_AMENDMENT_DEPTH:
            raise ValueError(f"Amendment depth {depth} exceeds maximum {MAX_AMENDMENT_DEPTH}")

        if scope is None:
            scope = set()

        score = germaneness(scope, original.scope)
        if score < GERMANENESS_THRESHOLD:
            raise ValueError(
                f"Amendment not germane (score {score:.2f} < {GERMANENESS_THRESHOLD})"
            )

        amendment_id = f"AMP-{original_motion_id.split('-', 1)[1]}-{uuid.uuid4().hex[:4].upper()}"
        amendment = self.motion_engine.create_motion(
            agent_id=agent_id,
            action=action,
            scope=scope,
            criticality_map=criticality_map,
            vote_method=original.vote_method,
        )
        # Patch the generated motion to be an amendment
        amendment.motion_id = amendment_id
        amendment.parent_id = original_motion_id
        amendment.depth = depth
        amendment.status = MotionStatus.DOCKET
        self.motion_engine.store.save_motion(amendment)
        return amendment

    def second_amendment(self, amendment_id: str, agent_id: str) -> Motion:
        return self.motion_engine.second_motion(amendment_id, agent_id)

    def get_amendment_tree(self, motion_id: str) -> Dict:
        original = self.motion_engine.get_motion(motion_id)
        if not original:
            raise ValueError(f"Motion {motion_id} not found")
        all_motions = self.motion_engine.list_motions()
        children = [m for m in all_motions if m.parent_id == motion_id]
        return {
            "motion_id": original.motion_id,
            "action": original.action,
            "status": original.status.value,
            "children": [
                {
                    "motion_id": c.motion_id,
                    "action": c.action,
                    "status": c.status.value,
                    "depth": c.depth,
                }
                for c in children
            ],
        }
