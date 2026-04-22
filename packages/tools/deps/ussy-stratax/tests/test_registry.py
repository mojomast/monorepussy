"""Tests for local probe registry."""
import json
import os
import tempfile
import pytest
from ussy_stratax.models import Probe
from ussy_stratax.registry.local import LocalRegistry


class TestLocalRegistry:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.registry = LocalRegistry(base_dir=self.tmpdir)

    def test_store_and_retrieve(self):
        probe = Probe(name="test_probe", package="pkg", function="fn")
        probe_id = self.registry.store_probe(probe)
        assert "pkg" in probe_id
        assert "fn" in probe_id

        retrieved = self.registry.get_probe("pkg", "fn", "test_probe")
        assert retrieved is not None
        assert retrieved.name == "test_probe"
        assert retrieved.package == "pkg"

    def test_get_nonexistent(self):
        result = self.registry.get_probe("nope", "fn", "test")
        assert result is None

    def test_list_all_probes(self):
        for i in range(5):
            self.registry.store_probe(
                Probe(name=f"probe_{i}", package="pkg", function=f"fn_{i}")
            )
        probes = self.registry.list_probes()
        assert len(probes) == 5

    def test_list_by_package(self):
        self.registry.store_probe(Probe(name="p1", package="pkg_a", function="fn1"))
        self.registry.store_probe(Probe(name="p2", package="pkg_a", function="fn2"))
        self.registry.store_probe(Probe(name="p3", package="pkg_b", function="fn1"))

        probes_a = self.registry.list_probes("pkg_a")
        assert len(probes_a) == 2

        probes_b = self.registry.list_probes("pkg_b")
        assert len(probes_b) == 1

    def test_delete_probe(self):
        self.registry.store_probe(Probe(name="p1", package="pkg", function="fn"))
        assert self.registry.delete_probe("pkg", "fn", "p1") is True
        assert self.registry.get_probe("pkg", "fn", "p1") is None

    def test_delete_nonexistent(self):
        assert self.registry.delete_probe("nope", "fn", "p1") is False

    def test_get_packages(self):
        self.registry.store_probe(Probe(name="p1", package="pkg_a", function="fn"))
        self.registry.store_probe(Probe(name="p2", package="pkg_b", function="fn"))
        packages = self.registry.get_packages()
        assert "pkg_a" in packages
        assert "pkg_b" in packages

    def test_probe_count(self):
        for i in range(3):
            self.registry.store_probe(
                Probe(name=f"p_{i}", package="pkg", function=f"fn_{i}")
            )
        assert self.registry.probe_count() == 3
        assert self.registry.probe_count("pkg") == 3
        assert self.registry.probe_count("other") == 0

    def test_store_with_all_fields(self):
        probe = Probe(
            name="full_probe",
            package="pkg",
            function="fn",
            input_data=[1, 2, 3],
            expected_output=6,
            output_has_keys=["a", "b"],
            returns_type="int",
        )
        self.registry.store_probe(probe)
        retrieved = self.registry.get_probe("pkg", "fn", "full_probe")
        assert retrieved is not None
        assert retrieved.input_data == [1, 2, 3]
        assert retrieved.expected_output == 6
