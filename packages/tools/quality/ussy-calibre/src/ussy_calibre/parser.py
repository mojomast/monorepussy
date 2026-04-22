"""JUnit XML test result parser."""

from __future__ import annotations

import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional

from ussy_calibre.models import TestOutcomeLevain as TestOutcome, TestResultLevain as TestResult


def parse_junit_xml(path: str) -> list[TestResult]:
    """Parse a JUnit XML file and return a list of TestResult objects."""
    results: list[TestResult] = []
    try:
        tree = ET.parse(path)
    except FileNotFoundError:
        return []
    root = tree.getroot()

    for testsuite in root.iter("testsuite"):
        ts_name = testsuite.get("name", "")
        for testcase in testsuite.iter("testcase"):
            name = testcase.get("name", "unknown")
            classname = testcase.get("classname", ts_name)
            time_str = testcase.get("time", "0")
            try:
                duration = float(time_str)
            except (ValueError, TypeError):
                duration = 0.0

            # Determine outcome
            outcome = TestOutcome.PASSED
            message = ""
            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")

            if failure is not None:
                outcome = TestOutcome.FAILED
                message = failure.text or failure.get("message", "")
            elif error is not None:
                outcome = TestOutcome.ERROR
                message = error.text or error.get("message", "")
            elif skipped is not None:
                outcome = TestOutcome.SKIPPED
                message = skipped.text or skipped.get("message", "")

            # Extract module from classname
            module = classname.rsplit(".", 1)[0] if "." in classname else classname

            # Build test_id
            test_id = f"{classname}::{name}"

            result = TestResult(
                test_id=test_id,
                name=name,
                module=module,
                outcome=outcome,
                duration=duration,
                timestamp=datetime.now(timezone.utc),
                message=message,
                filepath=classname.replace(".", "/") + ".py",
            )
            results.append(result)

    return results


def parse_junit_xml_string(xml_content: str) -> list[TestResult]:
    """Parse JUnit XML from a string."""
    root = ET.fromstring(xml_content)
    results: list[TestResult] = []

    for testsuite in root.iter("testsuite"):
        ts_name = testsuite.get("name", "")
        for testcase in testsuite.iter("testcase"):
            name = testcase.get("name", "unknown")
            classname = testcase.get("classname", ts_name)
            time_str = testcase.get("time", "0")
            try:
                duration = float(time_str)
            except (ValueError, TypeError):
                duration = 0.0

            outcome = TestOutcome.PASSED
            message = ""
            failure = testcase.find("failure")
            error = testcase.find("error")
            skipped = testcase.find("skipped")

            if failure is not None:
                outcome = TestOutcome.FAILED
                message = failure.text or failure.get("message", "")
            elif error is not None:
                outcome = TestOutcome.ERROR
                message = error.text or error.get("message", "")
            elif skipped is not None:
                outcome = TestOutcome.SKIPPED
                message = skipped.text or skipped.get("message", "")

            module = classname.rsplit(".", 1)[0] if "." in classname else classname
            test_id = f"{classname}::{name}"

            result = TestResult(
                test_id=test_id,
                name=name,
                module=module,
                outcome=outcome,
                duration=duration,
                timestamp=datetime.now(timezone.utc),
                message=message,
                filepath=classname.replace(".", "/") + ".py",
            )
            results.append(result)

    return results


def run_pytest_with_junit(
    test_path: str = ".",
    output_file: str = "levain-results.xml",
    extra_args: Optional[list[str]] = None,
) -> list[TestResult]:
    """Run pytest with JUnit XML output and parse the results."""
    cmd = [
        "python",
        "-m",
        "pytest",
        test_path,
        f"--junitxml={output_file}",
        "-q",
    ]
    if extra_args:
        cmd.extend(extra_args)

    try:
        subprocess.run(cmd, capture_output=True, timeout=300)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    if not os.path.exists(output_file):
        return []

    return parse_junit_xml(output_file)
