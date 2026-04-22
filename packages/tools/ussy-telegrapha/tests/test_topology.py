"""Tests for topology loading module."""

import json
import pytest
from pathlib import Path

from telegrapha.topology import (
    load_topology,
    parse_route_string,
    _parse_simple_yaml,
)


class TestParseRouteString:
    """Tests for route string parsing."""

    def test_arrow_separator(self):
        route = parse_route_string("order-service->payment->fraud-check->ledger")
        assert len(route.hops) == 4
        assert route.hops[0].name == "order-service"
        assert route.hops[3].name == "ledger"

    def test_unicode_arrow(self):
        route = parse_route_string("order→payment→ledger")
        assert len(route.hops) == 3

    def test_double_arrow(self):
        route = parse_route_string("a=>b=>c")
        assert len(route.hops) == 3

    def test_single_hop(self):
        route = parse_route_string("solo")
        assert len(route.hops) == 1
        assert route.hops[0].name == "solo"

    def test_whitespace_handling(self):
        route = parse_route_string("  a  ->  b  ->  c  ")
        assert len(route.hops) == 3


class TestLoadTopologyJSON:
    """Tests for JSON topology loading."""

    def test_load_valid_json(self, sample_topology_json):
        topology = load_topology(sample_topology_json)
        assert topology.name == "order-processing"
        assert len(topology.routes) == 2

    def test_route_names(self, sample_topology_json):
        topology = load_topology(sample_topology_json)
        assert topology.routes[0].name == "order-to-ledger"
        assert topology.routes[1].name == "api-to-db"

    def test_hop_data(self, sample_topology_json):
        topology = load_topology(sample_topology_json)
        route = topology.routes[0]
        assert len(route.hops) == 4
        assert route.hops[0].name == "order-service"
        assert route.hops[0].degradation == pytest.approx(0.005)
        assert route.hops[0].reliability == pytest.approx(0.9999)

    def test_metadata(self, sample_topology_json):
        topology = load_topology(sample_topology_json)
        assert topology.metadata.get("team") == "platform"


class TestLoadTopologyYAML:
    """Tests for YAML topology loading."""

    def test_load_valid_yaml(self, sample_topology_yaml):
        topology = load_topology(sample_topology_yaml)
        assert topology.name == "order-processing"

    def test_yaml_routes(self, sample_topology_yaml):
        topology = load_topology(sample_topology_yaml)
        assert len(topology.routes) >= 1


class TestLoadTopologyErrors:
    """Tests for error handling in topology loading."""

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_topology(tmp_path / "nonexistent.json")

    def test_empty_json(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("{}")
        topology = load_topology(p)
        assert topology.name == "unnamed"
        assert len(topology.routes) == 0


class TestSimpleYAMLParser:
    """Tests for the built-in YAML parser."""

    def test_basic_key_value(self):
        result = _parse_simple_yaml("name: test")
        assert result.get("name") == "test"

    def test_numeric_value(self):
        result = _parse_simple_yaml("count: 42")
        assert result.get("count") == 42

    def test_float_value(self):
        result = _parse_simple_yaml("rate: 0.99")
        assert result.get("rate") == pytest.approx(0.99)

    def test_boolean_value(self):
        result = _parse_simple_yaml("enabled: true")
        assert result.get("enabled") is True

    def test_comments_ignored(self):
        result = _parse_simple_yaml("# comment\nname: test")
        assert result.get("name") == "test"

    def test_quoted_string(self):
        result = _parse_simple_yaml('name: "test value"')
        assert result.get("name") == "test value"
