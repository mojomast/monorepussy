"""Quorum & Call-to-Order — Dynamic Participation Thresholds."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Set

from ussy_parliament.models import Agent, Motion, Session
from ussy_parliament.motion import compute_criticality_tier
from ussy_parliament.storage import SQLiteStore


def quorum_required(motion: Motion, total_active: int) -> int:
    """Compute required quorum based on motion criticality."""
    base_fraction = 0.3
    criticality_factor = motion.criticality_tier / 5.0
    adjusted_fraction = base_fraction + (0.4 * criticality_factor)
    return math.ceil(adjusted_fraction * total_active)


class QuorumEngine:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def call_to_order(
        self,
        motion_id: str,
        session_id: str,
        agents_present: Optional[Set[str]] = None,
    ) -> Session:
        motion = self.store.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        agents = self.store.list_agents()
        total_active = sum(1 for a in agents if a.active)
        required = quorum_required(motion, total_active)
        if agents_present is None:
            agents_present = set()
        verified = len(agents_present) >= required
        session = Session(
            session_id=session_id,
            motion_id=motion_id,
            agents_present=agents_present,
            quorum_required=required,
            quorum_verified=verified,
        )
        self.store.save_session(session)
        return session

    def join_session(self, session_id: str, agent_id: str) -> Session:
        session = self.store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.agents_present.add(agent_id)
        agents = self.store.list_agents()
        total_active = sum(1 for a in agents if a.active)
        motion = self.store.get_motion(session.motion_id)
        if motion:
            session.quorum_required = quorum_required(motion, total_active)
        session.quorum_verified = len(session.agents_present) >= session.quorum_required
        self.store.save_session(session)
        return session

    def leave_session(self, session_id: str, agent_id: str) -> Session:
        session = self.store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session.agents_present.discard(agent_id)
        agents = self.store.list_agents()
        total_active = sum(1 for a in agents if a.active)
        motion = self.store.get_motion(session.motion_id)
        if motion:
            session.quorum_required = quorum_required(motion, total_active)
        session.quorum_verified = len(session.agents_present) >= session.quorum_required
        self.store.save_session(session)
        return session

    def check_quorum(self, session_id: str) -> bool:
        session = self.store.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        return session.quorum_verified
