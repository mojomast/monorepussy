"""Tests for muscle memory — motor program compression."""

from __future__ import annotations

from propriocept.muscle_memory import (
    extract_commands,
    find_motor_programs,
    format_alias,
)


class TestFindMotorPrograms:
    def test_empty_commands(self) -> None:
        programs = find_motor_programs([])
        assert programs == {}

    def test_single_command_no_programs(self) -> None:
        programs = find_motor_programs(["git status"])
        assert programs == {}

    def test_basic_sequence(self) -> None:
        commands = ["git pull", "pytest", "git push"] * 7
        programs = find_motor_programs(commands, min_freq=5)
        assert ("git pull", "pytest", "git push") in programs
        assert programs[("git pull", "pytest", "git push")] == 7

    def test_sequence_with_noise(self) -> None:
        commands = []
        for i in range(10):
            if i % 3 == 0:
                commands.extend(["git pull", "pytest", "git push"])
            else:
                commands.append("ls")
                commands.append("git status")
        programs = find_motor_programs(commands, min_freq=2)
        assert ("git pull", "pytest", "git push") in programs
        # Single commands should not appear because min_len is 2
        assert ("ls",) not in programs

    def test_no_false_positives(self) -> None:
        commands = ["git pull", "pytest", "git push"] * 3
        programs = find_motor_programs(commands, min_freq=5)
        assert programs == {}

    def test_blacklist_ignored(self) -> None:
        commands = ["cd /tmp", "ls", "cd /home"] * 10
        programs = find_motor_programs(commands, min_freq=5)
        # cd and ls are blacklisted
        assert programs == {}

    def test_min_freq_filter(self) -> None:
        commands = ["git pull", "pytest"] * 4 + ["git pull", "pytest"] * 10
        programs = find_motor_programs(commands, min_freq=5)
        # 28 commands -> 27 overlapping windows of length 2
        # pattern appears at positions 0,2,4,...,26 -> 14 times
        assert programs[("git pull", "pytest")] == 14

    def test_max_len_respected(self) -> None:
        commands = ["a", "b", "c", "d", "e", "f"] * 10
        programs = find_motor_programs(commands, min_freq=5, max_len=3)
        for seq in programs:
            assert len(seq) <= 3

    def test_overlapping_sequences(self) -> None:
        commands = ["a", "b", "a", "b"] * 10
        programs = find_motor_programs(commands, min_freq=5)
        assert ("a", "b") in programs
        assert ("b", "a") in programs


class TestFormatAlias:
    def test_format_alias_basic(self) -> None:
        seq = ("git pull", "pytest")
        text = format_alias(seq, 5)
        assert "alias mp_git_pytest=" in text
        assert "git pull && pytest" in text
        assert "5 times" in text

    def test_format_alias_long(self) -> None:
        seq = ("git pull", "pytest", "git push", "deploy")
        text = format_alias(seq, 12)
        assert "12 times" in text


class TestExtractCommands:
    def test_extract_empty(self) -> None:
        assert extract_commands("") == []

    def test_extract_bash(self) -> None:
        text = "git status\nls -la\ncd /tmp\n"
        cmds = extract_commands(text)
        assert cmds == ["git status", "ls -la", "cd /tmp"]

    def test_extract_zsh_timestamps(self) -> None:
        text = ": 1234567890:0;git status\n: 1234567891:0;ls\n"
        cmds = extract_commands(text)
        assert cmds == ["git status", "ls"]

    def test_extract_skips_blank(self) -> None:
        text = "git status\n\nls\n"
        cmds = extract_commands(text)
        assert cmds == ["git status", "ls"]
