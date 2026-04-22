"""Tests for the core data model (stratagit.core)."""

import pytest
from datetime import datetime, timezone
from ussy_strata.core import (
    MineralType,
    IntrusionType,
    UnconformityType,
    StabilityTier,
    Stratum,
    Intrusion,
    Unconformity,
    FaultLine,
    Fossil,
    GeologicalReport,
    extension_to_mineral,
)


class TestMineralType:
    """Tests for mineral type enum and extension mapping."""

    def test_mineral_type_values(self):
        assert MineralType.PYTHON.value == "pyrite"
        assert MineralType.JAVASCRIPT.value == "fluorite"
        assert MineralType.RUST.value == "hematite"
        assert MineralType.OTHER.value == "clay"

    def test_extension_to_mineral_python(self):
        assert extension_to_mineral(".py") == MineralType.PYTHON

    def test_extension_to_mineral_javascript(self):
        assert extension_to_mineral(".js") == MineralType.JAVASCRIPT
        assert extension_to_mineral(".jsx") == MineralType.JAVASCRIPT

    def test_extension_to_mineral_typescript(self):
        assert extension_to_mineral(".ts") == MineralType.TYPESCRIPT
        assert extension_to_mineral(".tsx") == MineralType.TYPESCRIPT

    def test_extension_to_mineral_rust(self):
        assert extension_to_mineral(".rs") == MineralType.RUST

    def test_extension_to_mineral_go(self):
        assert extension_to_mineral(".go") == MineralType.GO

    def test_extension_to_mineral_c(self):
        assert extension_to_mineral(".c") == MineralType.C
        assert extension_to_mineral(".h") == MineralType.C

    def test_extension_to_mineral_cpp(self):
        assert extension_to_mineral(".cpp") == MineralType.CPP
        assert extension_to_mineral(".cc") == MineralType.CPP
        assert extension_to_mineral(".cxx") == MineralType.CPP

    def test_extension_to_mineral_markdown(self):
        assert extension_to_mineral(".md") == MineralType.MARKDOWN
        assert extension_to_mineral(".rst") == MineralType.MARKDOWN

    def test_extension_to_mineral_yaml(self):
        assert extension_to_mineral(".yml") == MineralType.YAML
        assert extension_to_mineral(".yaml") == MineralType.YAML

    def test_extension_to_mineral_json(self):
        assert extension_to_mineral(".json") == MineralType.JSON

    def test_extension_to_mineral_shell(self):
        assert extension_to_mineral(".sh") == MineralType.SHELL
        assert extension_to_mineral(".bash") == MineralType.SHELL

    def test_extension_to_mineral_unknown(self):
        assert extension_to_mineral(".xyz") == MineralType.OTHER
        assert extension_to_mineral(".exe") == MineralType.OTHER

    def test_extension_to_mineral_case_insensitive(self):
        assert extension_to_mineral(".PY") == MineralType.PYTHON
        assert extension_to_mineral(".Js") == MineralType.JAVASCRIPT

    def test_all_mineral_types_have_values(self):
        for mineral in MineralType:
            assert isinstance(mineral.value, str)
            assert len(mineral.value) > 0


class TestIntrusionType:
    def test_igneous(self):
        assert IntrusionType.IGNEOUS.value == "igneous"

    def test_sedimentary(self):
        assert IntrusionType.SEDIMENTARY.value == "sedimentary"


class TestUnconformityType:
    def test_rebase(self):
        assert UnconformityType.REBASE.value == "rebase"

    def test_squash(self):
        assert UnconformityType.SQUASH.value == "squash"

    def test_cherry_pick(self):
        assert UnconformityType.CHERRY_PICK.value == "cherry_pick"

    def test_orphan(self):
        assert UnconformityType.ORPHAN.value == "orphan"

    def test_force_push(self):
        assert UnconformityType.FORCE_PUSH.value == "force_push"


class TestStratum:
    def test_basic_creation(self):
        s = Stratum(
            commit_hash="abc123",
            author="Test",
            date=datetime.now(timezone.utc),
            message="test commit",
        )
        assert s.commit_hash == "abc123"
        assert s.author == "Test"
        assert s.message == "test commit"

    def test_default_values(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="test",
        )
        assert s.parent_hashes == []
        assert s.lines_added == 0
        assert s.lines_deleted == 0
        assert s.files_changed == []
        assert s.branch_name == ""
        assert s.stability_tier == ""

    def test_density_computation(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="test",
            lines_added=20,
            lines_deleted=10,
            files_changed=["a.py", "b.py"],
        )
        assert s.density == 15.0  # (20+10)/2

    def test_density_no_files(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="test",
        )
        assert s.density == 0.0

    def test_mineral_computation(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="test",
            files_changed=["app.py", "index.js"],
        )
        assert len(s.minerals) == 2
        assert s.minerals[0] == MineralType.PYTHON
        assert s.minerals[1] == MineralType.JAVASCRIPT

    def test_mineral_composition(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="test",
            files_changed=["a.py", "b.py", "c.js"],
        )
        comp = s.mineral_composition
        assert comp["pyrite"] == 2
        assert comp["fluorite"] == 1

    def test_thickness_computation(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="test",
            lines_added=50,
            lines_deleted=30,
        )
        assert s.thickness == 8.0  # (50+30)/10

    def test_thickness_minimum(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="test",
            lines_added=0,
            lines_deleted=0,
        )
        assert s.thickness == 0.1  # minimum

    def test_is_merge_true(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="merge",
            parent_hashes=["p1", "p2"],
        )
        assert s.is_merge is True

    def test_is_merge_false(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="normal",
            parent_hashes=["p1"],
        )
        assert s.is_merge is False

    def test_is_merge_no_parents(self):
        s = Stratum(
            commit_hash="abc",
            author="Test",
            date=datetime.now(timezone.utc),
            message="initial",
        )
        assert s.is_merge is False


class TestIntrusion:
    def test_basic_creation(self):
        intr = Intrusion(branch_name="feature/x")
        assert intr.branch_name == "feature/x"
        assert intr.intrusion_type == IntrusionType.IGNEOUS
        assert intr.commit_count == 0

    def test_duration_hours(self):
        intr = Intrusion(
            branch_name="test",
            start_date=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
        )
        assert intr.duration_hours == 4.0

    def test_duration_hours_no_dates(self):
        intr = Intrusion(branch_name="test")
        assert intr.duration_hours == 0.0

    def test_commits_per_hour(self):
        intr = Intrusion(
            branch_name="test",
            commit_count=10,
            start_date=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_date=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        )
        assert intr.commits_per_hour == 5.0

    def test_commits_per_hour_zero_duration(self):
        intr = Intrusion(branch_name="test", commit_count=5)
        assert intr.commits_per_hour == 0.0


class TestUnconformity:
    def test_basic_creation(self):
        u = Unconformity(
            unconformity_type=UnconformityType.REBASE,
            description="Test rebase",
        )
        assert u.unconformity_type == UnconformityType.REBASE
        assert u.confidence == 1.0

    def test_severity_major(self):
        u = Unconformity(
            unconformity_type=UnconformityType.REBASE,
            description="test",
            confidence=0.9,
        )
        assert u.severity == "major"

    def test_severity_moderate(self):
        u = Unconformity(
            unconformity_type=UnconformityType.SQUASH,
            description="test",
            confidence=0.6,
        )
        assert u.severity == "moderate"

    def test_severity_minor(self):
        u = Unconformity(
            unconformity_type=UnconformityType.CHERRY_PICK,
            description="test",
            confidence=0.3,
        )
        assert u.severity == "minor"


class TestFaultLine:
    def test_basic_creation(self):
        f = FaultLine(ref_name="refs/heads/main")
        assert f.ref_name == "refs/heads/main"

    def test_severity_label_catastrophic(self):
        f = FaultLine(ref_name="main", severity=0.9)
        assert f.severity_label == "catastrophic"

    def test_severity_label_major(self):
        f = FaultLine(ref_name="main", severity=0.6)
        assert f.severity_label == "major"

    def test_severity_label_minor(self):
        f = FaultLine(ref_name="main", severity=0.3)
        assert f.severity_label == "minor"


class TestFossil:
    def test_basic_creation(self):
        f = Fossil(
            name="old_function",
            kind="function",
            file_path="utils.py",
            deposited_hash="abc123",
        )
        assert f.name == "old_function"
        assert f.kind == "function"
        assert f.is_extinct is False

    def test_is_extinct(self):
        f = Fossil(
            name="old_function",
            kind="function",
            file_path="utils.py",
            deposited_hash="abc123",
            extinct_hash="def456",
        )
        assert f.is_extinct is True

    def test_lifespan_days(self):
        f = Fossil(
            name="old_function",
            kind="function",
            file_path="utils.py",
            deposited_hash="abc123",
            deposited_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            extinct_hash="def456",
            extinct_date=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
        assert f.lifespan_days == pytest.approx(31.0, abs=1.0)

    def test_lifespan_days_unknown(self):
        f = Fossil(
            name="old_function",
            kind="function",
            file_path="utils.py",
            deposited_hash="abc123",
        )
        assert f.lifespan_days == -1.0


class TestGeologicalReport:
    def test_default_report(self):
        report = GeologicalReport()
        assert report.total_strata == 0
        assert report.total_intrusions == 0
        assert report.strata == []
        assert report.intrusions == []
        assert report.fossils == []
        assert report.unconformities == []
        assert report.faults == []

    def test_fossil_density_empty(self):
        report = GeologicalReport()
        assert report.fossil_density == 0.0

    def test_fossil_density_with_data(self):
        report = GeologicalReport(total_strata=100, fossil_count=5)
        assert report.fossil_density == 50.0

    def test_dominant_mineral_empty(self):
        report = GeologicalReport()
        assert report.dominant_mineral == "unknown"

    def test_dominant_mineral_with_data(self):
        report = GeologicalReport(
            mineral_composition={"pyrite": 50, "fluorite": 30, "hematite": 20}
        )
        assert report.dominant_mineral == "pyrite"
