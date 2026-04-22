"""Tests for kinesthesia — context velocity tracking."""

from __future__ import annotations

from pathlib import Path

import pytest

from ussy_propriocept.kinesthesia import (
    compute_vectors,
    kinesthetic_velocity,
    parse_history,
)


class TestParseHistory:
    def test_parse_history_empty(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("")
        moves = parse_history(hist)
        assert moves == []

    def test_parse_history_missing(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        moves = parse_history(hist)
        assert moves == []

    def test_parse_history_cd(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("cd /home/user\ncd /tmp\ncd /var\n")
        moves = parse_history(hist)
        assert moves == [("nav", "/home/user"), ("nav", "/tmp"), ("nav", "/var")]

    def test_parse_history_git_checkout(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("git checkout main\ngit switch feature-x\n")
        moves = parse_history(hist)
        assert moves == [("branch", "main"), ("branch", "feature-x")]

    def test_parse_history_editors(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("vim file.py\ncode readme.md\nnano config.ini\n")
        moves = parse_history(hist)
        assert moves == [
            ("open", "file.py"),
            ("open", "readme.md"),
            ("open", "config.ini"),
        ]

    def test_parse_history_mixed(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text("ls\ncd /tmp\ngit checkout dev\nvim main.py\n")
        moves = parse_history(hist)
        assert moves == [("nav", "/tmp"), ("branch", "dev"), ("open", "main.py")]

    def test_parse_history_zsh_timestamp(self, tmp_path: Path) -> None:
        hist = tmp_path / "history"
        hist.write_text(": 1234567890:0;cd /tmp\n")
        moves = parse_history(hist)
        assert moves == [("nav", "/tmp")]


class TestKinestheticVelocity:
    def test_velocity_empty(self) -> None:
        assert kinesthetic_velocity([]) == 0.0

    def test_velocity_single(self) -> None:
        assert kinesthetic_velocity([("nav", "/tmp")]) == 0.0

    def test_velocity_zero(self) -> None:
        moves = [("nav", "/project")] * 50
        assert kinesthetic_velocity(moves) == 0.0

    def test_velocity_high(self) -> None:
        moves = []
        for _ in range(50):
            moves.append(("nav", "frontend"))
            moves.append(("nav", "backend"))
        v = kinesthetic_velocity(moves)
        assert v >= 0.9

    def test_velocity_window(self) -> None:
        old = [("nav", "/a")] * 100
        recent = [("nav", "frontend"), ("nav", "backend")] * 10
        v = kinesthetic_velocity(old + recent, window=20)
        assert v >= 0.9

    def test_velocity_partial(self) -> None:
        moves = [("nav", "/a"), ("nav", "/b")]
        v = kinesthetic_velocity(moves)
        assert v == 1.0


class TestComputeVectors:
    def test_compute_vectors_empty(self) -> None:
        vectors = compute_vectors([])
        assert vectors["total_moves"] == 0
        assert vectors["velocity"] == 0.0
        assert vectors["oscillation"] == 0.0
        assert vectors["flow_guard"] is False

    def test_compute_vectors_low_velocity(self) -> None:
        moves = [("nav", "/project")] * 50
        vectors = compute_vectors(moves)
        assert vectors["velocity"] == 0.0
        assert vectors["flow_guard"] is False

    def test_compute_vectors_high_velocity(self) -> None:
        moves = []
        for _ in range(50):
            moves.append(("nav", "frontend"))
            moves.append(("nav", "backend"))
        vectors = compute_vectors(moves)
        assert vectors["flow_guard"] is True
        assert vectors["velocity"] > 0.8

    def test_compute_vectors_oscillation(self) -> None:
        moves = [
            ("nav", "frontend"),
            ("nav", "backend"),
            ("nav", "frontend"),
            ("nav", "backend"),
        ]
        vectors = compute_vectors(moves)
        assert vectors["oscillation"] > 0.0
