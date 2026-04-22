"""JSON output formatter."""

import json
from stenography.models import ScanResult


class JsonFormatter:
    """Formats scan results as JSON."""

    def format(self, result: ScanResult) -> str:
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
