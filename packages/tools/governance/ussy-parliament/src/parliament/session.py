"""Session management tying all engines together."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from parliament.amendment import AmendmentEngine
from parliament.journal import JournalEngine
from parliament.models import (
    Agent,
    EntryType,
    Motion,
    MotionStatus,
    Session,
    ViolationType,
    VoteMethod,
)
from parliament.motion import MotionEngine
from parliament.points_of_order import PointsOfOrderEngine
from parliament.quorum import QuorumEngine
from parliament.storage import JournalStore, SQLiteStore
from parliament.voting import VotingEngine


class ParliamentSession:
    """Orchestrates all parliamentary engines for a chamber."""

    def __init__(self, chamber_dir: str | Path):
        self.chamber_dir = Path(chamber_dir)
        self.chamber_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.chamber_dir / "parliament.db"
        self.journal_path = self.chamber_dir / "journal.log"
        self.store = SQLiteStore(self.db_path)
        self.journal_store = JournalStore(self.journal_path)
        self.motion_engine = MotionEngine(self.store)
        self.amendment_engine = AmendmentEngine(self.motion_engine)
        self.quorum_engine = QuorumEngine(self.store)
        self.voting_engine = VotingEngine(self.store)
        self.poo_engine = PointsOfOrderEngine(self.store, self.quorum_engine)
        self.journal_engine = JournalEngine(self.journal_store)

    def init_chamber(self):
        """Ensure chamber directories and files exist."""
        self.chamber_dir.mkdir(parents=True, exist_ok=True)

    def register_agent(self, agent_id: str, agent_type: str, base_weight: float = 1.0, public_key: Optional[str] = None):
        agent = Agent(
            agent_id=agent_id,
            agent_type=agent_type,
            base_weight=base_weight,
            public_key=public_key,
        )
        self.store.save_agent(agent)
        self.journal_engine.append(
            EntryType.MOTION_INTRODUCED,
            {"event": "agent_registered", "agent_id": agent_id, "agent_type": agent_type},
        )
        return agent

    def create_motion(
        self,
        agent_id: str,
        action: str,
        scope: Optional[Set[str]] = None,
        criticality_map: Optional[Dict[str, float]] = None,
        vote_method: VoteMethod = VoteMethod.MAJORITY,
    ) -> Motion:
        motion = self.motion_engine.create_motion(
            agent_id=agent_id,
            action=action,
            scope=scope,
            criticality_map=criticality_map,
            vote_method=vote_method,
        )
        self.journal_engine.append(
            EntryType.MOTION_INTRODUCED,
            {
                "motion_id": motion.motion_id,
                "agent_id": agent_id,
                "action": action,
                "impact_score": motion.impact_score,
                "required_seconds": motion.required_seconds,
            },
            session_id=motion.motion_id,
        )
        return motion

    def second_motion(self, motion_id: str, agent_id: str) -> Motion:
        motion = self.motion_engine.second_motion(motion_id, agent_id)
        self.journal_engine.append(
            EntryType.SECONDED,
            {"motion_id": motion_id, "agent_id": agent_id, "current_seconds": len(motion.seconders)},
            session_id=motion_id,
        )
        if motion.status == MotionStatus.FLOOR:
            self.journal_engine.append(
                EntryType.GRADUATED_TO_FLOOR,
                {"motion_id": motion_id, "seconders": sorted(motion.seconders)},
                session_id=motion_id,
            )
        return motion

    def propose_amendment(
        self,
        original_motion_id: str,
        agent_id: str,
        action: str,
        scope: Optional[Set[str]] = None,
        criticality_map: Optional[Dict[str, float]] = None,
    ) -> Motion:
        amendment = self.amendment_engine.propose_amendment(
            original_motion_id=original_motion_id,
            agent_id=agent_id,
            action=action,
            scope=scope,
            criticality_map=criticality_map,
        )
        self.journal_engine.append(
            EntryType.AMENDMENT_PROPOSED,
            {
                "amendment_id": amendment.motion_id,
                "original_motion_id": original_motion_id,
                "agent_id": agent_id,
                "action": action,
            },
            session_id=original_motion_id,
        )
        return amendment

    def second_amendment(self, amendment_id: str, agent_id: str) -> Motion:
        motion = self.motion_engine.second_motion(amendment_id, agent_id)
        self.journal_engine.append(
            EntryType.AMENDMENT_SECONDED,
            {"amendment_id": amendment_id, "agent_id": agent_id},
            session_id=motion.parent_id or amendment_id,
        )
        return motion

    def call_to_order(self, motion_id: str, agents_present: Optional[Set[str]] = None) -> Session:
        session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"
        session = self.quorum_engine.call_to_order(motion_id, session_id, agents_present)
        self.journal_engine.append(
            EntryType.QUORUM_CALL,
            {
                "session_id": session_id,
                "motion_id": motion_id,
                "quorum_required": session.quorum_required,
                "present": len(session.agents_present),
                "verified": session.quorum_verified,
            },
            session_id=motion_id,
        )
        if session.quorum_verified:
            self.journal_engine.append(
                EntryType.QUORUM_ACHIEVED,
                {"session_id": session_id, "motion_id": motion_id},
                session_id=motion_id,
            )
        else:
            self.journal_engine.append(
                EntryType.QUORUM_DEFICIENT,
                {"session_id": session_id, "motion_id": motion_id},
                session_id=motion_id,
            )
        return session

    def open_voting(self, motion_id: str, method: Optional[VoteMethod] = None) -> Motion:
        motion = self.voting_engine.open_voting(motion_id, method)
        self.journal_engine.append(
            EntryType.VOTING_OPENED,
            {"motion_id": motion_id, "method": motion.vote_method.value},
            session_id=motion_id,
        )
        return motion

    def cast_vote(self, motion_id: str, agent_id: str, aye: bool) -> None:
        vote = self.voting_engine.cast_vote(motion_id, agent_id, aye)
        self.journal_engine.append(
            EntryType.VOTE_CAST,
            {"motion_id": motion_id, "agent_id": agent_id, "aye": aye, "weight": vote.weight},
            session_id=motion_id,
        )

    def close_voting(self, motion_id: str):
        result = self.voting_engine.close_voting(motion_id)
        self.journal_engine.append(
            EntryType.VOTING_CLOSED,
            {
                "motion_id": motion_id,
                "passes": result.passes,
                "tally": round(result.tally, 4),
                "method": result.method.value,
            },
            session_id=motion_id,
        )
        return result

    def raise_point_of_order(
        self,
        motion_id: str,
        violation_type: ViolationType,
        claimant: str,
        evidence: Optional[dict] = None,
    ):
        poo = self.poo_engine.raise_point_of_order(motion_id, violation_type, claimant, evidence)
        self.journal_engine.append(
            EntryType.POINT_OF_ORDER_RAISED,
            {"poo_id": poo.poo_id, "motion_id": motion_id, "violation": violation_type.value, "claimant": claimant},
            session_id=motion_id,
        )
        return poo

    def rule_on_point(self, poo_id: str):
        poo = self.poo_engine.rule(poo_id)
        self.journal_engine.append(
            EntryType.RULING_ISSUED,
            {
                "poo_id": poo.poo_id,
                "sustained": poo.sustained,
                "remedy": poo.remedy,
            },
            session_id=poo.motion_id,
        )
        return poo

    def file_appeal(self, poo_id: str, appealers: List[str]):
        appeal = self.poo_engine.file_appeal(poo_id, appealers)
        self.journal_engine.append(
            EntryType.APPEAL_FILED,
            {"appeal_id": appeal.appeal_id, "poo_id": poo_id, "appealers": appealers},
            session_id=appeal.motion_id,
        )
        return appeal

    def vote_appeal(self, appeal_id: str, votes):
        appeal = self.poo_engine.vote_appeal(appeal_id, votes)
        self.journal_engine.append(
            EntryType.APPEAL_OUTCOME,
            {"appeal_id": appeal_id, "outcome": appeal.outcome.value if appeal.outcome else None},
            session_id=appeal.motion_id,
        )
        return appeal

    def generate_minutes(self, session_id: str) -> str:
        minutes = self.journal_engine.generate_minutes(session_id)
        self.journal_engine.append(
            EntryType.MINUTES_PUBLISHED,
            {"session_id": session_id, "minutes_length": len(minutes)},
            session_id=session_id,
        )
        return minutes
