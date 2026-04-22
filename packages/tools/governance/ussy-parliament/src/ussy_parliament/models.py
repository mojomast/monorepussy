"""Core data models for Parliament."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Dict, List, Optional, Set


class MotionStatus(Enum):
    DOCKET = "docket"
    FLOOR = "floor"
    VOTING = "voting"
    PASSED = "passed"
    FAILED = "failed"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"


class VoteMethod(Enum):
    MAJORITY = "majority"
    SUPERMAJORITY = "supermajority"
    CONSENSUS = "consensus"


class EntryType(Enum):
    MOTION_INTRODUCED = "motion_introduced"
    SECONDED = "seconded"
    GRADUATED_TO_FLOOR = "graduated_to_floor"
    AMENDMENT_PROPOSED = "amendment_proposed"
    AMENDMENT_SECONDED = "amendment_seconded"
    QUORUM_CALL = "quorum_call"
    QUORUM_ACHIEVED = "quorum_achieved"
    QUORUM_DEFICIENT = "quorum_deficient"
    VOTING_OPENED = "voting_opened"
    VOTE_CAST = "vote_cast"
    VOTING_CLOSED = "voting_closed"
    POINT_OF_ORDER_RAISED = "point_of_order_raised"
    RULING_ISSUED = "ruling_issued"
    APPEAL_FILED = "appeal_filed"
    APPEAL_OUTCOME = "appeal_outcome"
    MINUTES_PUBLISHED = "minutes_published"


class ViolationType(Enum):
    QUORUM_DEFICIT = "quorum_deficit"
    UNGERMANE_AMENDMENT = "ungermane_amendment"
    MISSING_SECOND = "missing_second"
    VOTING_METHOD_MISMATCH = "voting_method_mismatch"
    DOUBLE_VOTING = "double_voting"


class RulingOutcome(Enum):
    SUSTAINED = "sustained"
    OVERTURNED = "overturned"


@dataclass
class Agent:
    agent_id: str
    agent_type: str
    base_weight: float = 1.0
    error_count_30d: int = 0
    public_key: Optional[str] = None
    active: bool = True

    @property
    def weight(self) -> float:
        return self.base_weight * (0.95**self.error_count_30d)


@dataclass
class Vote:
    agent_id: str
    aye: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    weight: float = 0.0


@dataclass
class Motion:
    motion_id: str
    agent_id: str
    action: str
    scope: Set[str] = field(default_factory=set)
    impact_score: float = 0.0
    required_seconds: int = 1
    seconders: Set[str] = field(default_factory=set)
    status: MotionStatus = MotionStatus.DOCKET
    parent_id: Optional[str] = None
    depth: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    vote_method: VoteMethod = VoteMethod.MAJORITY
    votes: List[Vote] = field(default_factory=list)
    criticality_tier: int = 1

    def __post_init__(self):
        if not self.scope:
            self.scope = set()
        if not self.seconders:
            self.seconders = set()
        if not self.votes:
            self.votes = []


@dataclass
class PointOfOrder:
    poo_id: str
    motion_id: str
    violation_type: ViolationType
    claimant: str
    evidence: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sustained: Optional[bool] = None
    remedy: Optional[str] = None


@dataclass
class Appeal:
    appeal_id: str
    poo_id: str
    motion_id: str
    appealers: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    outcome: Optional[RulingOutcome] = None
    votes: List[Vote] = field(default_factory=list)


@dataclass
class JournalEntry:
    entry_id: str
    timestamp: datetime
    entry_type: EntryType
    data: bytes
    previous_hash: bytes = field(default=b"")
    session_id: str = ""

    @property
    def hash(self) -> bytes:
        hasher = hashlib.sha256()
        hasher.update(self.previous_hash)
        hasher.update(self.timestamp.isoformat().encode("utf-8"))
        hasher.update(self.data)
        return hasher.digest()

    def to_dict(self) -> Dict:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "entry_type": self.entry_type.value,
            "data": self.data.decode("utf-8", errors="replace"),
            "previous_hash": self.previous_hash.hex(),
            "hash": self.hash.hex(),
            "session_id": self.session_id,
        }


@dataclass
class Session:
    session_id: str
    motion_id: str
    agents_present: Set[str] = field(default_factory=set)
    quorum_required: int = 0
    quorum_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.agents_present:
            self.agents_present = set()
