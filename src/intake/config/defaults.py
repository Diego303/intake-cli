"""Default values and constants for intake configuration."""

from __future__ import annotations

DEFAULT_MODEL = "claude-sonnet-4"
DEFAULT_LANGUAGE = "en"
DEFAULT_OUTPUT_DIR = "./specs"
DEFAULT_REQUIREMENTS_FORMAT = "ears"
DEFAULT_DESIGN_DEPTH = "moderate"
DEFAULT_TASK_GRANULARITY = "medium"
DEFAULT_EXPORT_FORMAT = "generic"
DEFAULT_CONFIG_FILENAME = ".intake.yaml"
DEFAULT_MAX_COST_PER_SPEC = 0.50
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 120

API_KEY_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
]
