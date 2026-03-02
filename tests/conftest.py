"""Shared test fixtures for all test modules."""

from __future__ import annotations

from pathlib import Path

import pytest
import structlog

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class _NullWriter:
    """A write target that silently discards all output.

    Unlike StringIO or file objects, this cannot be closed or garbage collected
    in a way that breaks structlog's cached loggers.
    """

    def write(self, msg: object) -> int:
        return 0

    def flush(self) -> None:
        pass


_NULL_WRITER = _NullWriter()


def _apply_null_structlog() -> None:
    """Apply structlog configuration with null writer."""
    structlog.reset_defaults()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=_NULL_WRITER),
        cache_logger_on_first_use=False,
    )


@pytest.fixture(autouse=True)
def _configure_structlog():
    """Configure structlog to use a null writer for tests.

    Uses a persistent _NullWriter that can never raise I/O errors.
    Resets both before and after each test to prevent pollution from
    CLI tests that call setup_logging().
    """
    _apply_null_structlog()
    yield
    _apply_null_structlog()


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def markdown_fixture(fixtures_dir: Path) -> Path:
    """Path to the simple Markdown spec fixture."""
    return fixtures_dir / "simple_spec.md"


@pytest.fixture
def plaintext_fixture(fixtures_dir: Path) -> Path:
    """Path to the Slack thread plaintext fixture."""
    return fixtures_dir / "slack_thread.txt"


@pytest.fixture
def yaml_fixture(fixtures_dir: Path) -> Path:
    """Path to the structured YAML requirements fixture."""
    return fixtures_dir / "structured_reqs.yaml"


@pytest.fixture
def jira_fixture(fixtures_dir: Path) -> Path:
    """Path to the Jira JSON export fixture (API format)."""
    return fixtures_dir / "jira_export.json"


@pytest.fixture
def jira_multi_fixture(fixtures_dir: Path) -> Path:
    """Path to the Jira JSON export fixture (list format)."""
    return fixtures_dir / "jira_export_multi.json"


@pytest.fixture
def confluence_fixture(fixtures_dir: Path) -> Path:
    """Path to the Confluence HTML export fixture."""
    return fixtures_dir / "confluence_page.html"


@pytest.fixture
def image_fixture(fixtures_dir: Path) -> Path:
    """Path to the test image fixture."""
    return fixtures_dir / "wireframe.png"


@pytest.fixture
def tmp_yaml_config(tmp_path: Path) -> Path:
    """Create a temporary .intake.yaml for config tests."""
    config_content = """\
llm:
  model: gpt-4o
  max_cost_per_spec: 1.00
project:
  name: test-project
  language: en
spec:
  output_dir: ./custom-specs
  design_depth: detailed
"""
    config_path = tmp_path / ".intake.yaml"
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def invalid_yaml_config(tmp_path: Path) -> Path:
    """Create an invalid .intake.yaml for error tests."""
    config_path = tmp_path / ".intake.yaml"
    config_path.write_text("invalid: yaml: [broken: {")
    return config_path
