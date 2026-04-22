"""Voting Methods Engine — Pluggable Decision Resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ussy_parliament.models import Agent, Motion, MotionStatus, Vote, VoteMethod
from ussy_parliament.storage import SQLiteStore

VETO_THRESHOLD = 0.5


@dataclass
class VoteResult:
    passes: bool
    tally: float
    weighted_yes: float
    weighted_no: float
    total_weight: float
    method: VoteMethod


def tally_votes(votes: List[Vote], method: VoteMethod) -> VoteResult:
    weighted_yes = sum(v.weight for v in votes if v.aye)
    weighted_no = sum(v.weight for v in votes if not v.aye)
    total_weight = weighted_yes + weighted_no

    if total_weight == 0:
        return VoteResult(passes=False, tally=0.0, weighted_yes=0.0, weighted_no=0.0, total_weight=0.0, method=method)

    ratio = weighted_yes / total_weight
    passes = False
    if method == VoteMethod.MAJORITY:
        passes = ratio > 0.5
    elif method == VoteMethod.SUPERMAJORITY:
        passes = ratio >= 2 / 3
    elif method == VoteMethod.CONSENSUS:
        max_no_weight = max((v.weight for v in votes if not v.aye), default=0)
        passes = ratio >= 0.8 and max_no_weight < VETO_THRESHOLD

    return VoteResult(
        passes=passes,
        tally=ratio,
        weighted_yes=weighted_yes,
        weighted_no=weighted_no,
        total_weight=total_weight,
        method=method,
    )


class VotingEngine:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def open_voting(self, motion_id: str, method: Optional[VoteMethod] = None) -> Motion:
        motion = self.store.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        if motion.status != MotionStatus.FLOOR:
            raise ValueError(f"Motion {motion_id} is not on the floor")
        if method:
            motion.vote_method = method
        motion.status = MotionStatus.VOTING
        self.store.save_motion(motion)
        return motion

    def cast_vote(self, motion_id: str, agent_id: str, aye: bool) -> Vote:
        motion = self.store.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        if motion.status != MotionStatus.VOTING:
            raise ValueError(f"Motion {motion_id} is not open for voting")

        existing = [v for v in self.store.get_votes(motion_id) if v.agent_id == agent_id]
        if existing:
            raise ValueError(f"Agent {agent_id} has already voted on motion {motion_id}")

        agent = self.store.get_agent(agent_id)
        weight = agent.weight if agent else 1.0
        vote = Vote(agent_id=agent_id, aye=aye, weight=weight)
        self.store.save_vote(vote, motion_id)
        return vote

    def close_voting(self, motion_id: str) -> VoteResult:
        motion = self.store.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        if motion.status != MotionStatus.VOTING:
            raise ValueError(f"Motion {motion_id} is not open for voting")

        votes = self.store.get_votes(motion_id)
        result = tally_votes(votes, motion.vote_method)
        motion.status = MotionStatus.PASSED if result.passes else MotionStatus.FAILED
        self.store.save_motion(motion)
        return result

    def get_result(self, motion_id: str) -> VoteResult:
        motion = self.store.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        votes = self.store.get_votes(motion_id)
        return tally_votes(votes, motion.vote_method)
