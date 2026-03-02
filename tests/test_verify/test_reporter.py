"""Tests for verification report formatters."""

from __future__ import annotations

import json
from xml.etree.ElementTree import fromstring

import pytest

from intake.verify.engine import CheckResult, VerificationReport
from intake.verify.reporter import (
    JsonReporter,
    JunitReporter,
    Reporter,
    TerminalReporter,
    get_reporter,
)


@pytest.fixture
def sample_report() -> VerificationReport:
    """Create a sample verification report."""
    return VerificationReport(
        spec_name="test-spec",
        total_checks=3,
        passed=2,
        failed=1,
        skipped=0,
        results=[
            CheckResult(
                id="check-1",
                name="Unit tests",
                passed=True,
                required=True,
                output="All tests passed",
                duration_ms=150,
            ),
            CheckResult(
                id="check-2",
                name="Files exist",
                passed=True,
                required=True,
                output="All 3 file(s) exist",
                duration_ms=5,
            ),
            CheckResult(
                id="check-3",
                name="Security scan",
                passed=False,
                required=False,
                error="Pattern found in config.py",
                duration_ms=20,
            ),
        ],
        all_required_passed=True,
    )


def test_terminal_reporter_renders(sample_report: VerificationReport) -> None:
    """Terminal reporter returns a summary string."""
    reporter = TerminalReporter()
    summary = reporter.render(sample_report)

    assert "passed" in summary.lower()
    assert isinstance(summary, str)


def test_json_reporter_valid_json(sample_report: VerificationReport) -> None:
    """JSON reporter produces valid JSON."""
    reporter = JsonReporter()
    output = reporter.render(sample_report)

    data = json.loads(output)
    assert data["spec_name"] == "test-spec"
    assert data["total_checks"] == 3
    assert data["passed"] == 2
    assert data["failed"] == 1
    assert data["all_required_passed"] is True
    assert len(data["results"]) == 3


def test_json_reporter_includes_result_details(sample_report: VerificationReport) -> None:
    """JSON reporter includes all result fields."""
    reporter = JsonReporter()
    data = json.loads(reporter.render(sample_report))

    first = data["results"][0]
    assert first["id"] == "check-1"
    assert first["name"] == "Unit tests"
    assert first["passed"] is True
    assert first["duration_ms"] == 150


def test_junit_reporter_valid_xml(sample_report: VerificationReport) -> None:
    """JUnit reporter produces valid XML."""
    reporter = JunitReporter()
    output = reporter.render(sample_report)

    root = fromstring(output)
    assert root.tag == "testsuites"
    suites = root.findall("testsuite")
    assert len(suites) == 1
    assert suites[0].attrib["name"] == "test-spec"


def test_junit_reporter_includes_failures(sample_report: VerificationReport) -> None:
    """JUnit reporter includes failure elements for failed checks."""
    reporter = JunitReporter()
    output = reporter.render(sample_report)

    root = fromstring(output)
    failures = root.findall(".//failure")
    assert len(failures) == 1
    assert "Pattern found" in failures[0].attrib["message"]


def test_junit_reporter_counts(sample_report: VerificationReport) -> None:
    """JUnit reporter has correct test counts."""
    reporter = JunitReporter()
    output = reporter.render(sample_report)

    root = fromstring(output)
    suite = root.find("testsuite")
    assert suite is not None
    assert suite.attrib["tests"] == "3"
    assert suite.attrib["failures"] == "1"


def test_get_reporter_terminal() -> None:
    """get_reporter returns a TerminalReporter for 'terminal'."""
    reporter = get_reporter("terminal")
    assert isinstance(reporter, TerminalReporter)


def test_get_reporter_json() -> None:
    """get_reporter returns a JsonReporter for 'json'."""
    reporter = get_reporter("json")
    assert isinstance(reporter, JsonReporter)


def test_get_reporter_junit() -> None:
    """get_reporter returns a JunitReporter for 'junit'."""
    reporter = get_reporter("junit")
    assert isinstance(reporter, JunitReporter)


def test_get_reporter_invalid_raises() -> None:
    """get_reporter raises ValueError for unknown format."""
    with pytest.raises(ValueError, match="Unknown report format"):
        get_reporter("invalid")


def test_reporters_satisfy_protocol() -> None:
    """All reporters satisfy the Reporter protocol."""
    assert isinstance(TerminalReporter(), Reporter)
    assert isinstance(JsonReporter(), Reporter)
    assert isinstance(JunitReporter(), Reporter)
