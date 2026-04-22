"""Data models for the application."""

from dataclasses import dataclass, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class User:
    id: int
    name: str
    email: str
    created_at: Optional[datetime] = None
    is_active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            created_at=row.get("created_at"),
            is_active=row.get("is_active", True),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(**data)


@dataclass
class Project:
    id: int
    name: str
    description: str
    owner_id: int
    status: str = "active"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Task:
    id: int
    title: str
    description: str
    project_id: int
    assignee_id: Optional[int] = None
    status: str = "todo"
    priority: str = "medium"

    def to_dict(self) -> dict:
        return asdict(self)
