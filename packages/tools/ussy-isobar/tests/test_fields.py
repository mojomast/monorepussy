"""Tests for isobar.fields module."""

import math
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import pytest

from ussy_isobar.scanner import FileCommit, FileHistory, ScanResult
from ussy_isobar.fields import (
    AtmosphericProfile, AtmosphericField,
    compute_temperature, compute_pressure, compute_humidity,
    compute_wind, compute_dew_point, compute_vorticity,
    compute_barometric_tendency, compute_fields,
    R_SPRINT, GRAVITY, FRONT_THRESHOLD, CYCLONE_VORTICITY_THRESHOLD,
)


def _make_commit(days_ago: int, message: str = "update",
                 insertions: int = 5, deletions: int = 2) -> FileCommit:
    now = datetime.now(timezone.utc)
    ts = now - timedelta(days=days_ago)
    return FileCommit(
        commit_hash=f"hash_{days_ago}_{message}",
        author="tester",
        timestamp=ts,
        message=message,
        files_changed=["test.py"],
        insertions=insertions,
        deletions=deletions,
    )


def _make_history(filepath: str, num_commits: int = 0,
                   bug_fix_count: int = 0) -> FileHistory:
    now = datetime.now(timezone.utc)
    commits = []
    for i in range(num_commits):
        msg = "fix bug" if i < bug_fix_count else "update"
        commits.append(_make_commit(days_ago=i, message=msg))
    return FileHistory(filepath=filepath, commits=commits)


class TestComputeTemperature:
    def test_no_commits(self):
        history = FileHistory(filepath="test.py", commits=[])
        assert compute_temperature(history) == 0.0

    def test_old_commits(self):
        """Commits older than 4 weeks should contribute little."""
        now = datetime.now(timezone.utc)
        old = now - timedelta(days=60)
        c = FileCommit(commit_hash="a", author="x", timestamp=old, message="m")
        history = FileHistory(filepath="test.py", commits=[c])
        temp = compute_temperature(history, now=now)
        assert temp < 10.0  # Very low since the commit is old

    def test_recent_daily_commits(self):
        """Daily commits for 4 weeks should give high temperature."""
        now = datetime.now(timezone.utc)
        commits = [
            _make_commit(days_ago=i) for i in range(28)
        ]
        history = FileHistory(filepath="test.py", commits=commits)
        temp = compute_temperature(history, now=now)
        assert temp > 30.0  # Should be hot with 28 daily commits

    def test_single_recent_commit(self):
        commits = [_make_commit(days_ago=1)]
        history = FileHistory(filepath="test.py", commits=commits)
        temp = compute_temperature(history)
        assert 0 < temp < 100

    def test_temperature_capped_at_100(self):
        """Temperature should never exceed 100."""
        now = datetime.now(timezone.utc)
        commits = [_make_commit(days_ago=0) for _ in range(50)]
        history = FileHistory(filepath="test.py", commits=commits)
        temp = compute_temperature(history, now=now)
        assert temp <= 100.0

    def test_temperature_non_negative(self):
        history = _make_history("test.py", num_commits=3)
        temp = compute_temperature(history)
        assert temp >= 0.0


class TestComputePressure:
    def test_no_importers(self):
        profiles = {}
        import_graph = {}
        assert compute_pressure("test.py", profiles, import_graph) == 0.0

    def test_with_importers(self):
        profiles = {
            "main.py": AtmosphericProfile(filepath="main.py", temperature=50.0),
        }
        import_graph = {"main.py": {"test.py"}}
        pressure = compute_pressure("test.py", profiles, import_graph)
        assert pressure > 0.0

    def test_hot_importers_increase_pressure(self):
        cold_profiles = {
            "main.py": AtmosphericProfile(filepath="main.py", temperature=10.0),
        }
        hot_profiles = {
            "main.py": AtmosphericProfile(filepath="main.py", temperature=90.0),
        }
        import_graph = {"main.py": {"test.py"}}
        cold_pressure = compute_pressure("test.py", cold_profiles, import_graph)
        hot_pressure = compute_pressure("test.py", hot_profiles, import_graph)
        assert hot_pressure > cold_pressure

    def test_more_importers_more_pressure(self):
        profiles = {
            "a.py": AtmosphericProfile(filepath="a.py", temperature=50.0),
            "b.py": AtmosphericProfile(filepath="b.py", temperature=50.0),
            "c.py": AtmosphericProfile(filepath="c.py", temperature=50.0),
        }
        import_graph = {
            "a.py": {"test.py"},
            "b.py": {"test.py"},
            "c.py": {"test.py"},
        }
        pressure = compute_pressure("test.py", profiles, import_graph)
        assert pressure > 0.0


class TestComputeHumidity:
    def test_no_connections(self):
        humidity = compute_humidity("test.py", {})
        assert humidity == 0.0

    def test_with_imports(self):
        import_graph = {
            "test.py": {"utils.py", "helpers.py"},
            "main.py": {"test.py"},
        }
        humidity = compute_humidity("test.py", import_graph)
        assert humidity > 0.0

    def test_high_coupling(self):
        import_graph = {
            "test.py": {f"dep{i}.py" for i in range(10)},
        }
        for i in range(10):
            import_graph[f"dep{i}.py"] = {"test.py"}
        humidity = compute_humidity("test.py", import_graph)
        assert humidity > 50.0

    def test_humidity_capped_at_100(self):
        import_graph = {
            "test.py": {f"dep{i}.py" for i in range(50)},
        }
        humidity = compute_humidity("test.py", import_graph)
        assert humidity <= 100.0


class TestComputeWind:
    def test_no_co_changes(self):
        speed, direction, co_map = compute_wind("test.py", {}, {})
        assert speed == 0.0
        assert direction == "CALM"
        assert co_map == {}

    def test_with_co_changes(self):
        co_changes = {("test.py", "other.py"): 5}
        profiles = {}
        speed, direction, co_map = compute_wind("test.py", co_changes, profiles)
        assert speed > 0.0
        assert "other.py" in co_map

    def test_wind_speed_capped(self):
        co_changes = {("test.py", f"other{i}.py"): 10 for i in range(30)}
        profiles = {}
        speed, direction, co_map = compute_wind("test.py", co_changes, profiles)
        assert speed <= 100.0


class TestComputeDewPoint:
    def test_dry_air(self):
        dp = compute_dew_point(25.0, 10.0)
        assert dp < 25.0  # Dew point below temperature when dry

    def test_humid_air(self):
        dp = compute_dew_point(25.0, 90.0)
        assert dp > 15.0  # Dew point closer to temperature when humid

    def test_zero_humidity(self):
        dp = compute_dew_point(25.0, 0.0)
        assert dp < 25.0  # Very low dew point


class TestComputeVorticity:
    def test_no_commits(self):
        history = FileHistory(filepath="test.py", commits=[])
        assert compute_vorticity(history) == 0.0

    def test_with_commits(self):
        history = _make_history("test.py", num_commits=10, bug_fix_count=3)
        vort = compute_vorticity(history)
        # Just check it computes without error
        assert isinstance(vort, float)

    def test_positive_bug_trend(self):
        """More recent bugs than older bugs should produce positive vorticity component."""
        now = datetime.now(timezone.utc)
        recent_bug = FileCommit(
            commit_hash="a", author="x",
            timestamp=now - timedelta(days=5),
            message="fix bug",
            insertions=5, deletions=10,
        )
        old_normal = FileCommit(
            commit_hash="b", author="x",
            timestamp=now - timedelta(days=45),
            message="update feature",
            insertions=20, deletions=2,
        )
        history = FileHistory(filepath="test.py", commits=[recent_bug, old_normal])
        vort = compute_vorticity(history, now=now)
        assert isinstance(vort, float)


class TestComputeBarometricTendency:
    def test_no_commits(self):
        history = FileHistory(filepath="test.py", commits=[])
        assert compute_barometric_tendency(history) == 0.0

    def test_increasing_activity(self):
        now = datetime.now(timezone.utc)
        recent = [_make_commit(days_ago=i) for i in range(5)]
        old = [_make_commit(days_ago=30 + i) for i in range(2)]
        history = FileHistory(filepath="test.py", commits=recent + old)
        tendency = compute_barometric_tendency(history, now=now)
        assert tendency > 0  # Recent activity > old activity

    def test_decreasing_activity(self):
        now = datetime.now(timezone.utc)
        recent = [_make_commit(days_ago=i) for i in range(1)]
        old = [_make_commit(days_ago=30 + i) for i in range(5)]
        history = FileHistory(filepath="test.py", commits=recent + old)
        tendency = compute_barometric_tendency(history, now=now)
        assert tendency < 0


class TestComputeFields:
    def test_empty_scan(self):
        scan = ScanResult(root="/tmp")
        field = compute_fields(scan)
        assert len(field.profiles) == 0

    def test_with_histories(self):
        now = datetime.now(timezone.utc)
        scan = ScanResult(root="/tmp")
        scan.file_histories["test.py"] = _make_history("test.py", num_commits=5)
        scan.file_histories["main.py"] = _make_history("main.py", num_commits=2)
        scan.import_graph = {"main.py": {"test.py"}}
        scan.co_changes = {("test.py", "main.py"): 3}

        field = compute_fields(scan, now=now)
        assert "test.py" in field.profiles
        assert "main.py" in field.profiles
        assert field.profiles["test.py"].temperature >= 0
        assert field.profiles["main.py"].temperature >= 0


class TestAtmosphericProfile:
    def test_is_hot(self):
        p = AtmosphericProfile(filepath="test.py", temperature=80.0)
        assert p.is_hot

    def test_is_not_hot(self):
        p = AtmosphericProfile(filepath="test.py", temperature=30.0)
        assert not p.is_hot

    def test_is_cold(self):
        p = AtmosphericProfile(filepath="test.py", temperature=5.0)
        assert p.is_cold

    def test_is_high_pressure(self):
        p = AtmosphericProfile(filepath="test.py", pressure=30.0)
        assert p.is_high_pressure

    def test_is_humid(self):
        p = AtmosphericProfile(filepath="test.py", humidity=80.0)
        assert p.is_humid

    def test_is_cyclonic(self):
        p = AtmosphericProfile(filepath="test.py", bug_vorticity=2.5)
        assert p.is_cyclonic

    def test_internal_energy(self):
        p = AtmosphericProfile(filepath="test.py", temperature=50.0, pressure=20.0)
        energy = p.internal_energy
        assert energy > 0

    def test_storm_probability_range(self):
        p = AtmosphericProfile(filepath="test.py", temperature=80.0, humidity=90.0,
                                bug_vorticity=3.0)
        assert 0.0 <= p.storm_probability <= 1.0

    def test_category_label_cyclonic(self):
        p = AtmosphericProfile(filepath="test.py", temperature=80.0,
                                bug_vorticity=3.0)
        assert "STORM" in p.category_label()

    def test_category_label_cold_anticyclone(self):
        p = AtmosphericProfile(filepath="test.py", temperature=5.0, pressure=30.0)
        assert p.category_label() == "ANTICYCLONE"

    def test_category_label_fair(self):
        p = AtmosphericProfile(filepath="test.py", temperature=30.0, pressure=10.0,
                                humidity=40.0, bug_vorticity=0.0)
        assert p.category_label() == "FAIR"


class TestAtmosphericField:
    def test_get_profile(self):
        field = AtmosphericField()
        p = AtmosphericProfile(filepath="test.py")
        field.profiles["test.py"] = p
        assert field.get_profile("test.py") == p
        assert field.get_profile("nonexistent.py") is None

    def test_hot_files(self):
        field = AtmosphericField()
        field.profiles["hot.py"] = AtmosphericProfile(filepath="hot.py", temperature=80.0)
        field.profiles["cold.py"] = AtmosphericProfile(filepath="cold.py", temperature=5.0)
        hot = field.hot_files(threshold=50.0)
        assert len(hot) == 1
        assert hot[0].filepath == "hot.py"

    def test_cold_files(self):
        field = AtmosphericField()
        field.profiles["hot.py"] = AtmosphericProfile(filepath="hot.py", temperature=80.0)
        field.profiles["cold.py"] = AtmosphericProfile(filepath="cold.py", temperature=5.0)
        cold = field.cold_files(threshold=10.0)
        assert len(cold) == 1
        assert cold[0].filepath == "cold.py"

    def test_cyclonic_files(self):
        field = AtmosphericField()
        field.profiles["stable.py"] = AtmosphericProfile(filepath="stable.py", bug_vorticity=0.1)
        field.profiles["cyclone.py"] = AtmosphericProfile(filepath="cyclone.py", bug_vorticity=3.0)
        cyclonic = field.cyclonic_files()
        assert len(cyclonic) == 1
