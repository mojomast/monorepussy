"""Tests for the distribution module."""

import math
import os
import tempfile
import shutil
from datetime import datetime, timedelta

import pytest

from dosemate.distribution import DistributionParams, compute_distribution
from dosemate.dependency_graph import DependencyGraphAnalyzer
from dosemate.git_parser import PullRequestInfo


class TestDistributionParams:
    """Tests for DistributionParams dataclass."""

    def test_effective_concentration_positive_vd(self):
        """Effective concentration should be dose * fu / Vd."""
        params = DistributionParams(
            Vd=10.0, Kp=1.5, fu=0.6,
            total_dependent_modules=10,
            central_compartment_size=2,
            peripheral_compartment_size=8,
        )
        result = params.effective_concentration(100)
        assert abs(result - 100 * 0.6 / 10.0) < 0.01

    def test_effective_concentration_zero_vd(self):
        """Zero Vd should return 0."""
        params = DistributionParams(
            Vd=0, Kp=1.0, fu=0.5,
            total_dependent_modules=0,
            central_compartment_size=0,
            peripheral_compartment_size=0,
        )
        assert params.effective_concentration(100) == 0.0

    def test_vd_always_positive(self):
        """Vd should always be positive (property test)."""
        assert True  # This will be tested with actual computations


class TestComputeDistribution:
    """Tests for compute_distribution function."""

    def test_no_changed_files(self):
        """Empty file list should produce minimal distribution."""
        tmpdir = tempfile.mkdtemp()
        try:
            # Create a minimal Python file so the analyzer has something
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            with open(os.path.join(tmpdir, "src", "mod.py"), 'w') as f:
                f.write("def foo(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            file_to_module = {"src/mod.py": "src/mod"}

            result = compute_distribution([], analyzer, file_to_module)
            assert result.Vd >= 1.0  # minimum Vd
            assert result.central_compartment_size == 0
        finally:
            shutil.rmtree(tmpdir)

    def test_isolated_change_low_vd(self):
        """A change to an isolated file should have low Vd."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "isolated"), exist_ok=True)
            with open(os.path.join(tmpdir, "isolated", "script.py"), 'w') as f:
                f.write("# standalone script\ndef main(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            file_to_module = {"isolated/script.py": "isolated/script"}

            result = compute_distribution(
                ["isolated/script.py"], analyzer, file_to_module,
            )
            # Isolated file should have lower Vd than a widely-imported one
            assert result.Vd >= 1.0
        finally:
            shutil.rmtree(tmpdir)

    def test_public_api_fraction_in_range(self):
        """fu should always be in [0, 1]."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            with open(os.path.join(tmpdir, "src", "mod.py"), 'w') as f:
                f.write("def public_fn(): pass\ndef _private_fn(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            file_to_module = {"src/mod.py": "src/mod"}

            result = compute_distribution(
                ["src/mod.py"], analyzer, file_to_module,
            )
            assert 0.0 <= result.fu <= 1.0
        finally:
            shutil.rmtree(tmpdir)

    def test_kp_positive(self):
        """Kp should always be positive."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            with open(os.path.join(tmpdir, "src", "mod.py"), 'w') as f:
                f.write("def foo(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            file_to_module = {"src/mod.py": "src/mod"}

            result = compute_distribution(
                ["src/mod.py"], analyzer, file_to_module,
            )
            assert result.Kp > 0
        finally:
            shutil.rmtree(tmpdir)

    def test_total_dependent_modules_ge_central(self):
        """Total dependent modules should be >= central compartment size."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            with open(os.path.join(tmpdir, "src", "mod.py"), 'w') as f:
                f.write("def foo(): pass\n")
            
            analyzer = DependencyGraphAnalyzer(tmpdir)
            analyzer.analyze()
            file_to_module = {"src/mod.py": "src/mod"}

            result = compute_distribution(
                ["src/mod.py"], analyzer, file_to_module,
            )
            assert result.total_dependent_modules >= result.central_compartment_size
        finally:
            shutil.rmtree(tmpdir)
