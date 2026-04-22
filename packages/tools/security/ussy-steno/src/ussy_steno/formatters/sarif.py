"""SARIF (Static Analysis Results Interchange Format) output formatter."""

import json
from ussy_steno.models import ScanResult, Severity


_SEVERITY_TO_SARIF_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}


class SarifFormatter:
    """Formats scan results as SARIF JSON."""

    def format(self, result: ScanResult) -> str:
        rules = {}
        results = []

        for finding in result.findings:
            rule_id = finding.rule_id or "STEN000"
            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "shortDescription": {"text": f"Stenography rule: {rule_id}"},
                    "properties": {"tags": ["security", "steganography"]},
                }

            results.append({
                "ruleId": rule_id,
                "level": _SEVERITY_TO_SARIF_LEVEL.get(finding.severity, "note"),
                "message": {"text": finding.message},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.file},
                        "region": {
                            "startLine": finding.line,
                            "startColumn": finding.column,
                        },
                    }
                }],
                "properties": {
                    "scanner": finding.scanner,
                    "context": finding.context.value,
                    "charCode": finding.char_code,
                },
            })

        sarif = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {
                    "driver": {
                        "name": "Stenography",
                        "version": "1.0.0",
                        "informationUri": "https://github.com/mojomast/stenographussy",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "invocations": [{
                    "executionSuccessful": True,
                    "toolExecutionNotifications": [],
                }],
            }],
        }

        return json.dumps(sarif, indent=2, ensure_ascii=False)
