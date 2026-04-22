"""Test fixtures for Tarot — sample decision cards and data."""

import os
import json
import tempfile

# Sample decision card markdown content
ADR_001_CONTENT = """---
adr_id: ADR-001
title: PostgreSQL for session storage
confidence: High
created_at: "2025-01-15T10:00:00+00:00"
outcomes:
  - "Schema rigidity:35%"
  - "No issues:65%"
cascades:
  - "ADR-003:Redis cluster needed:60%"
interactions:
  - "ADR-002:AMPLIFY:1.3"
tags:
  - database
  - storage
---

# ADR-001: PostgreSQL for session storage

We chose PostgreSQL for session storage over Redis.
"""

ADR_002_CONTENT = """---
adr_id: ADR-002
title: Microservices migration
confidence: Medium
created_at: "2025-01-20T10:00:00+00:00"
outcomes:
  - "Distributed monolith:40%"
  - "No issues:60%"
cascades:
  - "ADR-004:Service mesh needed:50%"
interactions:
  - "ADR-001:AMPLIFY:1.5"
  - "ADR-003:MITIGATE:2.0"
tags:
  - architecture
---

# ADR-002: Microservices migration

We are migrating to microservices.
"""

ADR_003_CONTENT = """---
adr_id: ADR-003
title: Redis cluster for caching
confidence: High
created_at: "2025-02-01T10:00:00+00:00"
outcomes:
  - "Memory pressure:20%"
  - "No issues:80%"
interactions:
  - "ADR-002:MITIGATE:1.8"
tags:
  - cache
  - database
---

# ADR-003: Redis cluster for caching

Adding Redis cluster for caching layer.
"""

ADR_004_CONTENT = """---
adr_id: ADR-004
title: Service mesh adoption
confidence: Low
created_at: "2025-02-10T10:00:00+00:00"
outcomes:
  - "Debugging complexity:50%"
  - "Performance overhead:20%"
  - "No issues:30%"
tags:
  - infrastructure
---

# ADR-004: Service mesh adoption

Adopting a service mesh for observability.
"""

# High-risk card for death reading tests
ADR_005_CONTENT = """---
adr_id: ADR-005
title: Single AZ deployment
confidence: Low
outcomes:
  - "Availability outage:70%"
  - "No issues:30%"
cascades:
  - "ADR-002:Cascading failures:80%"
tags:
  - infrastructure
  - risk
---

# ADR-005: Single AZ deployment

Deploying to a single availability zone to save costs.
"""

# Sample incidents JSON
INCIDENTS_JSON = [
    {
        "incident_id": "INC-001",
        "title": "Session storage outage",
        "severity": "high",
        "affected_adrs": ["ADR-001"],
        "timestamp": "2025-03-15T14:30:00+00:00",
        "description": "PostgreSQL connection pool exhausted",
        "resolution": "Increased pool size and added connection timeout"
    },
    {
        "incident_id": "INC-002",
        "title": "Cascading microservice failure",
        "severity": "critical",
        "affected_adrs": ["ADR-002", "ADR-005"],
        "timestamp": "2025-04-01T09:00:00+00:00",
        "description": "Single AZ went down, all microservices failed",
        "resolution": "Migrated to multi-AZ deployment"
    },
    {
        "incident_id": "INC-003",
        "title": "Redis memory pressure",
        "severity": "medium",
        "affected_adrs": ["ADR-003"],
        "timestamp": "2025-04-10T16:00:00+00:00",
        "description": "Redis OOM during peak traffic",
        "resolution": "Added eviction policy and increased memory"
    }
]


def create_fixture_dir():
    """Create a temporary directory with fixture decision cards."""
    tmpdir = tempfile.mkdtemp(prefix="tarot_test_")

    for name, content in [
        ("adr-001.md", ADR_001_CONTENT),
        ("adr-002.md", ADR_002_CONTENT),
        ("adr-003.md", ADR_003_CONTENT),
        ("adr-004.md", ADR_004_CONTENT),
        ("adr-005.md", ADR_005_CONTENT),
    ]:
        with open(os.path.join(tmpdir, name), "w") as f:
            f.write(content)

    return tmpdir


def create_incidents_file():
    """Create a temporary JSON file with sample incidents."""
    tmpfile = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, prefix="tarot_incidents_"
    )
    json.dump(INCIDENTS_JSON, tmpfile)
    tmpfile.close()
    return tmpfile.name
