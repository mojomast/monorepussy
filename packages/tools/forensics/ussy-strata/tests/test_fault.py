"""Tests for fault line detection (stratagit.core.fault)."""

import pytest
from stratagit.core.fault import detect_faults
from stratagit.core import FaultLine


class TestDetectFaults:
    def test_returns_list(self, git_repo):
        result = detect_faults(git_repo)
        assert isinstance(result, list)

    def test_items_are_fault_lines(self, git_repo):
        result = detect_faults(git_repo)
        for f in result:
            assert isinstance(f, FaultLine)

    def test_fault_has_ref_name(self, git_repo):
        result = detect_faults(git_repo)
        for f in result:
            assert f.ref_name

    def test_fault_severity_range(self, git_repo):
        result = detect_faults(git_repo)
        for f in result:
            assert 0 <= f.severity <= 1.0

    def test_fault_severity_label(self, git_repo):
        result = detect_faults(git_repo)
        for f in result:
            assert f.severity_label in ("catastrophic", "major", "minor")

    def test_sorted_by_date(self, git_repo):
        result = detect_faults(git_repo)
        if len(result) > 1:
            dates = [f.date for f in result if f.date is not None]
            for i in range(len(dates) - 1):
                assert dates[i] >= dates[i + 1]
