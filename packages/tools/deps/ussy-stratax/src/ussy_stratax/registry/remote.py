"""Remote registry client — interact with the community probe registry."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ussy_stratax.models import Probe


class RemoteRegistry:
    """Client for the remote Strata community probe registry.

    In production, this would communicate with a hosted API.
    For now, it provides the interface and can work with a mock server.
    """

    DEFAULT_URL = "https://registry.strata.dev"

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        self.url = (url or self.DEFAULT_URL).rstrip("/")
        self.api_key = api_key

    def search_probes(self, package: str, function: Optional[str] = None) -> List[Probe]:
        """Search the remote registry for probes targeting a package."""
        try:
            import requests

            params: Dict[str, str] = {"package": package}
            if function:
                params["function"] = function

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            resp = requests.get(
                f"{self.url}/api/v1/probes",
                params=params,
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()

            probes = []
            for item in resp.json().get("probes", []):
                probes.append(self._dict_to_probe(item))
            return probes

        except ImportError:
            return []
        except Exception:
            return []

    def submit_probe(self, probe: Probe) -> Optional[str]:
        """Submit a probe to the remote registry."""
        try:
            import requests

            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            resp = requests.post(
                f"{self.url}/api/v1/probes",
                json=probe.to_dict(),
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()

            return resp.json().get("probe_id")

        except ImportError:
            return None
        except Exception:
            return None

    def get_bedrock_scores(self, package: str) -> Dict[str, float]:
        """Get community bedrock scores for a package."""
        try:
            import requests

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            resp = requests.get(
                f"{self.url}/api/v1/scores/{package}",
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()

            return resp.json().get("scores", {})

        except ImportError:
            return {}
        except Exception:
            return {}

    def get_package_versions(self, package: str) -> List[str]:
        """Fetch available versions for a package from PyPI."""
        try:
            import requests

            resp = requests.get(
                f"https://pypi.org/pypi/{package}/json",
                timeout=10,
            )
            resp.raise_for_status()

            releases = resp.json().get("releases", {})
            return sorted(releases.keys())

        except ImportError:
            return []
        except Exception:
            return []

    def _dict_to_probe(self, data: Dict[str, Any]) -> Probe:
        """Convert a dict to a Probe object."""
        return Probe(
            name=data.get("name", ""),
            package=data.get("package", ""),
            function=data.get("function", ""),
            input_data=data.get("input_data"),
            expected_output=data.get("expected_output"),
            output_has_keys=data.get("output_has_keys"),
            target_mutated=data.get("target_mutated"),
            raises=data.get("raises"),
            returns_type=data.get("returns_type"),
            custom_assertion=data.get("custom_assertion"),
        )
