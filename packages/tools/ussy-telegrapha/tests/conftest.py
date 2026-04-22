"""Shared test fixtures for Telegrapha."""

import json
from pathlib import Path

import pytest

from ussy_telegrapha.models import Hop, Route, PipelineTopology, DLQEntry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_topology_json():
    """Path to sample topology JSON file."""
    return FIXTURES_DIR / "sample_topology.json"


@pytest.fixture
def sample_topology_yaml():
    """Path to sample topology YAML file."""
    return FIXTURES_DIR / "sample_topology.yaml"


@pytest.fixture
def sample_dlq_json():
    """Path to sample DLQ JSON file."""
    return FIXTURES_DIR / "sample_dlq.json"


@pytest.fixture
def sample_precedence_json():
    """Path to sample precedence config JSON file."""
    return FIXTURES_DIR / "sample_precedence.json"


@pytest.fixture
def simple_route():
    """A simple 4-hop route with known degradation factors."""
    return Route(
        name="test-route",
        hops=[
            Hop(name="hop1", degradation=0.005, reliability=0.9999),
            Hop(name="hop2", degradation=0.030, reliability=0.9995),
            Hop(name="hop3", degradation=0.020, reliability=0.9998),
            Hop(name="hop4", degradation=0.040, reliability=0.9990),
        ],
    )


@pytest.fixture
def distortionless_route():
    """A route that meets the distortionless condition."""
    return Route(
        name="distortionless-route",
        hops=[
            Hop(name="hop1", degradation=0.01, reliability=0.999,
                serialization_degradation=0.005, deserialization_degradation=0.005),
            Hop(name="hop2", degradation=0.01, reliability=0.999,
                serialization_degradation=0.005, deserialization_degradation=0.005),
        ],
    )


@pytest.fixture
def distorted_route():
    """A route that does NOT meet the distortionless condition."""
    return Route(
        name="distorted-route",
        hops=[
            Hop(name="hop1", degradation=0.01, reliability=0.999,
                serialization_degradation=0.020, deserialization_degradation=0.001),
            Hop(name="hop2", degradation=0.01, reliability=0.999,
                serialization_degradation=0.020, deserialization_degradation=0.001),
        ],
    )


@pytest.fixture
def high_reliability_route():
    """A route with high per-hop reliability."""
    return Route(
        name="high-rel-route",
        hops=[
            Hop(name="gw", reliability=0.9999),
            Hop(name="auth", reliability=0.9999),
            Hop(name="svc", reliability=0.9999),
        ],
    )


@pytest.fixture
def mixed_reliability_route():
    """A route with one weak hop."""
    return Route(
        name="mixed-rel-route",
        hops=[
            Hop(name="gw", reliability=0.9999),
            Hop(name="auth", reliability=0.9995),  # weak link
            Hop(name="svc", reliability=0.9998),
        ],
    )


@pytest.fixture
def sample_dlq_entries():
    """Sample DLQ entries for testing."""
    return [
        DLQEntry(id="msg-001", failure_type="no_response", source_hop="fraud-service", age_hours=2.5),
        DLQEntry(id="msg-002", failure_type="destination_closed", source_hop="fraud-service", age_hours=1.8),
        DLQEntry(id="msg-003", failure_type="address_undecipherable", source_hop="order-service", age_hours=4.2),
        DLQEntry(id="msg-004", failure_type="no_response", source_hop="fraud-service", age_hours=3.1),
        DLQEntry(id="msg-005", failure_type="destination_closed", source_hop="payment-service", age_hours=0.5),
    ]


@pytest.fixture
def empty_route():
    """An empty route with no hops."""
    return Route(name="empty-route", hops=[])


@pytest.fixture
def single_hop_route():
    """A route with a single hop."""
    return Route(
        name="single-hop",
        hops=[Hop(name="solo", degradation=0.02, reliability=0.998)],
    )
