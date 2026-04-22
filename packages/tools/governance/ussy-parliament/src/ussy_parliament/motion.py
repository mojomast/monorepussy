"""Motion & Seconding Engine — Proposal Initiation with Dynamic Sponsorship."""

from __future__ import annotations

import math
import uuid
from typing import Dict, List, Optional, Set

from ussy_parliament.models import Agent, Motion, MotionStatus, VoteMethod
from ussy_parliament.storage import SQLiteStore


def compute_impact_score(scope: Set[str], criticality_map: Optional[Dict[str, float]] = None) -> float:
    """Compute impact score from scope."""
    if criticality_map is None:
        criticality_map = {}
    total = 0.0
    for item in scope:
        crit = criticality_map.get(item, 1.0)
        total += crit * 1.0  # recency factor default 1.0
    return total


def compute_required_seconds(impact_score: float, policy_cap: int = 7) -> int:
    """Dynamic threshold: max(1, ceil(ln(impact_score + 1))), capped by policy."""
    if impact_score <= 0:
        return 1
    required = max(1, math.ceil(math.log(impact_score + 1)))
    return min(required, policy_cap)


def compute_criticality_tier(impact_score: float) -> int:
    """Tier 1-5 based on log10 of impact score."""
    if impact_score <= 0:
        return 1
    tier = math.ceil(math.log10(impact_score))
    return max(1, min(5, tier))


class MotionEngine:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def create_motion(
        self,
        agent_id: str,
        action: str,
        scope: Optional[Set[str]] = None,
        criticality_map: Optional[Dict[str, float]] = None,
        vote_method: VoteMethod = VoteMethod.MAJORITY,
    ) -> Motion:
        if scope is None:
            scope = set()
        motion_id = f"MP-{uuid.uuid4().hex[:8].upper()}"
        impact_score = compute_impact_score(scope, criticality_map)
        required_seconds = compute_required_seconds(impact_score)
        criticality_tier = compute_criticality_tier(impact_score)
        motion = Motion(
            motion_id=motion_id,
            agent_id=agent_id,
            action=action,
            scope=scope,
            impact_score=impact_score,
            required_seconds=required_seconds,
            vote_method=vote_method,
            criticality_tier=criticality_tier,
        )
        self.store.save_motion(motion)
        return motion

    def second_motion(self, motion_id: str, agent_id: str) -> Motion:
        motion = self.store.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        if motion.status != MotionStatus.DOCKET:
            raise ValueError(f"Motion {motion_id} is not on the docket")
        motion.seconders.add(agent_id)
        if len(motion.seconders) >= motion.required_seconds:
            motion.status = MotionStatus.FLOOR
        self.store.save_motion(motion)
        return motion

    def withdraw_second(self, motion_id: str, agent_id: str) -> Motion:
        motion = self.store.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        motion.seconders.discard(agent_id)
        if len(motion.seconders) < motion.required_seconds and motion.status == MotionStatus.FLOOR:
            motion.status = MotionStatus.DOCKET
        self.store.save_motion(motion)
        return motion

    def get_motion(self, motion_id: str) -> Optional[Motion]:
        return self.store.get_motion(motion_id)

    def list_motions(self) -> List[Motion]:
        return self.store.list_motions()

    def graduate_if_ready(self, motion_id: str) -> Motion:
        motion = self.store.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        if len(motion.seconders) >= motion.required_seconds:
            motion.status = MotionStatus.FLOOR
        else:
            motion.status = MotionStatus.DOCKET
        self.store.save_motion(motion)
        return motion
