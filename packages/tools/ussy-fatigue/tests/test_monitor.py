"""Tests for the structural health monitor module."""

import os
import tempfile
import pytest

from fatigue.monitor import (
    get_changed_files,
    get_previous_K,
    save_K,
    format_alert,
    run_monitor,
)
from fatigue.models import MaterialConstants


class TestGetChangedFiles:
    """Tests for getting changed files from git."""

    def test_non_git_directory(self):
        """Test get_changed_files outside a git repo."""
        files = get_changed_files("HEAD")
        # May return empty list if not in a git repo
        assert isinstance(files, list)

    def test_returns_list(self):
        """Test that result is always a list."""
        result = get_changed_files("HEAD")
        assert isinstance(result, list)


class TestKHistory:
    """Tests for K value history tracking."""

    def test_save_and_retrieve_K(self, tmp_path):
        """Test saving and retrieving K values."""
        history_file = str(tmp_path / ".fatigue_history")

        save_K("module_a.py", 15.5, history_file)
        save_K("module_b.py", 28.3, history_file)

        assert get_previous_K("module_a.py", history_file) == 15.5
        assert get_previous_K("module_b.py", history_file) == 28.3

    def test_update_K(self, tmp_path):
        """Test updating an existing K value."""
        history_file = str(tmp_path / ".fatigue_history")

        save_K("module_a.py", 15.5, history_file)
        save_K("module_a.py", 20.0, history_file)

        assert get_previous_K("module_a.py", history_file) == 20.0

    def test_nonexistent_module(self, tmp_path):
        """Test retrieving K for a module not in history."""
        history_file = str(tmp_path / ".fatigue_history")
        result = get_previous_K("nonexistent.py", history_file)
        assert result is None

    def test_nonexistent_history_file(self):
        """Test retrieving K when history file doesn't exist."""
        result = get_previous_K("any.py", "/nonexistent/.fatigue_history")
        assert result is None

    def test_corrupted_history_file(self, tmp_path):
        """Test handling of corrupted history file."""
        history_file = str(tmp_path / ".fatigue_history")
        with open(history_file, "w") as f:
            f.write("corrupted data\nmore bad data\n")

        result = get_previous_K("any.py", history_file)
        assert result is None


class TestFormatAlert:
    """Tests for alert formatting."""

    def test_basic_alert(self):
        """Test basic alert formatting."""
        alert = format_alert(
            file_path="module.py",
            K=30.0,
            prev_K=None,
            material=MaterialConstants(),
            growth_rate=1.5,
        )
        assert "module.py" in alert
        assert "30.0" in alert
        assert "1.50" in alert

    def test_alert_above_K_Ic(self):
        """Test alert when K is above fracture toughness."""
        alert = format_alert(
            file_path="critical.py",
            K=35.0,
            prev_K=30.0,
            material=MaterialConstants(K_Ic=28.0),
            growth_rate=3.0,
        )
        assert "FRACTURE TOUGHNESS" in alert

    def test_alert_above_K_e(self):
        """Test alert when K is above endurance limit."""
        alert = format_alert(
            file_path="growing.py",
            K=10.0,
            prev_K=None,
            material=MaterialConstants(K_e=8.2),
            growth_rate=0.5,
        )
        assert "endurance limit" in alert

    def test_alert_with_previous_K(self):
        """Test alert showing change from previous K."""
        alert = format_alert(
            file_path="module.py",
            K=25.0,
            prev_K=20.0,
            material=MaterialConstants(),
            growth_rate=1.0,
        )
        assert "+5.0" in alert  # Increase shown

    def test_alert_decreasing_K(self):
        """Test alert when K decreased."""
        alert = format_alert(
            file_path="module.py",
            K=15.0,
            prev_K=20.0,
            material=MaterialConstants(),
            growth_rate=0.3,
        )
        assert "5.0" in alert  # Decrease shown

    def test_alert_accelerating(self):
        """Test alert for accelerating growth."""
        alert = format_alert(
            file_path="module.py",
            K=35.0,
            prev_K=30.0,
            material=MaterialConstants(K_Ic=28.0),
            growth_rate=2.5,
        )
        assert "ACCELERATING" in alert or "Recommend" in alert


class TestRunMonitor:
    """Tests for the full monitoring run."""

    def test_monitor_no_git(self, tmp_path):
        """Test monitoring outside a git repo."""
        material = MaterialConstants()
        alerts = run_monitor(str(tmp_path), material, commit="HEAD")
        # Should return a list (may be empty if no git)
        assert isinstance(alerts, list)

    def test_monitor_returns_list(self):
        """Test that monitor always returns a list."""
        alerts = run_monitor(".", MaterialConstants())
        assert isinstance(alerts, list)
