"""Points of Order & Appeals — Procedural Challenge and Override."""

from __future__ import annotations

import uuid
from typing import List, Optional

from parliament.models import (
    Agent,
    Appeal,
    Motion,
    MotionStatus,
    PointOfOrder,
    RulingOutcome,
    ViolationType,
    Vote,
    VoteMethod,
)
from parliament.quorum import QuorumEngine
from parliament.storage import SQLiteStore
from parliament.voting import tally_votes


class PointsOfOrderEngine:
    def __init__(self, store: SQLiteStore, quorum_engine: QuorumEngine):
        self.store = store
        self.quorum_engine = quorum_engine

    def raise_point_of_order(
        self,
        motion_id: str,
        violation_type: ViolationType,
        claimant: str,
        evidence: Optional[dict] = None,
    ) -> PointOfOrder:
        if evidence is None:
            evidence = {}
        poo_id = f"POO-{uuid.uuid4().hex[:8].upper()}"
        poo = PointOfOrder(
            poo_id=poo_id,
            motion_id=motion_id,
            violation_type=violation_type,
            claimant=claimant,
            evidence=evidence,
        )
        self.store.save_point_of_order(poo)
        return poo

    def rule(self, poo_id: str) -> PointOfOrder:
        poo = self.store.get_point_of_order(poo_id)
        if not poo:
            raise ValueError(f"Point of order {poo_id} not found")
        if poo.sustained is not None:
            return poo

        sustained = False
        remedy = None

        if poo.violation_type == ViolationType.QUORUM_DEFICIT:
            session = self.store.get_session_by_motion(poo.motion_id)
            sustained = session is None or not session.quorum_verified
            if sustained:
                remedy = "suspend_target"
        elif poo.violation_type == ViolationType.UNGERMANE_AMENDMENT:
            # Would need amendment context; simplified: look up motion depth > 0
            motion = self.store.get_motion(poo.motion_id)
            sustained = motion is not None and motion.depth > 0
            if sustained:
                remedy = "reject_amendment"
        elif poo.violation_type == ViolationType.MISSING_SECOND:
            motion = self.store.get_motion(poo.motion_id)
            sustained = motion is not None and len(motion.seconders) < motion.required_seconds
            if sustained:
                remedy = "return_to_docket"
        elif poo.violation_type == ViolationType.VOTING_METHOD_MISMATCH:
            motion = self.store.get_motion(poo.motion_id)
            if motion:
                expected = VoteMethod.SUPERMAJORITY if motion.criticality_tier >= 4 else motion.vote_method
                sustained = motion.vote_method != expected
            if sustained:
                remedy = "change_method"
        elif poo.violation_type == ViolationType.DOUBLE_VOTING:
            votes = self.store.get_votes(poo.motion_id)
            agents = [v.agent_id for v in votes]
            sustained = len(agents) != len(set(agents))
            if sustained:
                remedy = "invalidate_duplicate_votes"

        poo.sustained = sustained
        poo.remedy = remedy
        self.store.save_point_of_order(poo)

        if sustained and remedy == "suspend_target":
            motion = self.store.get_motion(poo.motion_id)
            if motion:
                motion.status = MotionStatus.SUSPENDED
                self.store.save_motion(motion)

        return poo

    def file_appeal(self, poo_id: str, appealers: List[str]) -> Appeal:
        if len(appealers) < 2:
            raise ValueError("At least 2 appealers required")
        poo = self.store.get_point_of_order(poo_id)
        if not poo:
            raise ValueError(f"Point of order {poo_id} not found")
        appeal_id = f"APL-{uuid.uuid4().hex[:8].upper()}"
        appeal = Appeal(
            appeal_id=appeal_id,
            poo_id=poo_id,
            motion_id=poo.motion_id,
            appealers=appealers,
        )
        self.store.save_appeal(appeal)
        return appeal

    def vote_appeal(self, appeal_id: str, votes: List[Vote]) -> Appeal:
        appeal = self.store.get_appeal(appeal_id)
        if not appeal:
            raise ValueError(f"Appeal {appeal_id} not found")
        result = tally_votes(votes, VoteMethod.SUPERMAJORITY)
        appeal.outcome = RulingOutcome.OVERTURNED if result.passes else RulingOutcome.SUSTAINED
        self.store.save_appeal(appeal)
        if appeal.outcome == RulingOutcome.OVERTURNED:
            poo = self.store.get_point_of_order(appeal.poo_id)
            if poo:
                poo.sustained = False
                poo.remedy = None
                self.store.save_point_of_order(poo)
            motion = self.store.get_motion(appeal.motion_id)
            if motion and motion.status == MotionStatus.SUSPENDED:
                motion.status = MotionStatus.FLOOR
                self.store.save_motion(motion)
        return appeal
