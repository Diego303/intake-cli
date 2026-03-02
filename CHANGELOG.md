# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-02

### Added

#### Phase 1 — Ingest (8 parsers + registry)

- **Project scaffolding**: `pyproject.toml` with hatchling build system, `src/intake/` package layout with 10 subpackages.
- **CLI framework**: Click-based CLI with 8 commands (`init`, `add`, `verify`, `export`, `show`, `list`, `diff`, `doctor`).
- **`intake doctor` command**: Full environment health check — validates Python version (3.12+), LLM API keys, optional dependencies (pdfplumber, python-docx, bs4, markdownify, litellm, jinja2), and `.intake.yaml` config validity. Outputs a Rich table with PASS/FAIL status and fix hints.
- **Configuration system**: Pydantic v2 models for all config (`LLMConfig`, `ProjectConfig`, `SpecConfig`, `VerificationConfig`, `ExportConfig`, `SecurityConfig`). Layered merge: defaults → preset → `.intake.yaml` → CLI flags.
- **Configuration presets**: `--preset minimal|standard|enterprise` for quick setup. Minimal is cheap/fast for prototyping, standard is balanced, enterprise is detailed with full traceability.
- **8 input parsers** — all producing normalized `ParsedContent`:
  - `MarkdownParser` — `.md` files with YAML front matter support and heading-based section extraction.
  - `PlaintextParser` — `.txt` files, stdin (`-`), Slack thread dumps. Paragraph-level sections.
  - `YamlInputParser` — `.yaml`/`.yml`/`.json` structured requirements. Section extraction from top-level keys.
  - `PdfParser` — `.pdf` files via pdfplumber. Text + table extraction (tables converted to Markdown).
  - `DocxParser` — `.docx` files via python-docx. Text, tables, heading-based sections, document metadata (author, title, date).
  - `JiraParser` — Jira JSON exports (both `{"issues":[...]}` API format and `[{"key":...}]` list format). Extracts issues with summary, description, comments (last 5), labels, priority, status, and inter-issue links.
  - `ConfluenceParser` — Confluence HTML exports via BeautifulSoup4 + markdownify. Detects Confluence markers, extracts main content, converts to clean Markdown.
  - `ImageParser` — `.png`/`.jpg`/`.jpeg`/`.webp`/`.gif` via injectable LLM vision callable. Ships with a stub; real vision analysis enabled when LLM adapter is configured.
- **Parser registry**: `ParserRegistry` with automatic format detection by file extension and content inspection. JSON subtype detection (Jira vs generic), HTML subtype detection (Confluence vs generic). Factory function `create_default_registry()` registers all 8 parsers.
- **Utilities**:
  - `file_detect.py` — Extension-based format detection with `EXTENSION_MAP`.
  - `project_detect.py` — Auto-detects project tech stack from 20+ marker files (pyproject.toml, package.json, Dockerfile, etc.) and content patterns (fastapi, django, react, etc.).
  - `cost.py` — `CostTracker` for LLM cost accumulation with per-phase breakdown.
  - `logging.py` — structlog configuration with console/JSON rendering.

#### Phase 2 — Analyze (LLM orchestration)

- **LLM Adapter** (`llm/adapter.py`): LiteLLM wrapper with async completion, retry with exponential backoff, cost tracking per call, budget enforcement (`CostLimitError`), JSON response parsing with markdown fence stripping, API key validation. Custom exceptions: `LLMError`, `CostLimitError`, `APIKeyMissingError`.
- **Analysis pipeline** (`analyze/`):
  - `analyzer.py` — Orchestrator: coordinates extraction → deduplication → conflict validation → risk assessment → design phases. Supports multi-source analysis with automatic text combining.
  - `prompts.py` — Three system prompts: `EXTRACTION_PROMPT` (requirements, conflicts, questions), `RISK_ASSESSMENT_PROMPT` (risk analysis per requirement), `DESIGN_PROMPT` (architecture, tasks, acceptance checks).
  - `extraction.py` — Parses LLM JSON output into typed `AnalysisResult` with requirements, conflicts, and open questions.
  - `dedup.py` — Jaccard word similarity deduplication across sources (threshold: 0.75).
  - `conflicts.py` — Validates extracted conflicts, filters incomplete entries.
  - `questions.py` — Validates extracted open questions, filters incomplete entries.
  - `risks.py` — Parses LLM risk assessment into typed `RiskItem` list.
  - `design.py` — Parses LLM design output into `DesignResult` with components, file actions, tasks, and acceptance checks.
  - `models.py` — 10 dataclasses: `Requirement`, `Conflict`, `OpenQuestion`, `RiskItem`, `TechDecision`, `TaskItem`, `FileAction`, `AcceptanceCheck`, `DesignResult`, `AnalysisResult`.

#### Phase 3 — Generate (spec files + lock)

- **Generation module** (`generate/`):
  - `spec_builder.py` — Orchestrates rendering of 6 spec files via Jinja2 templates + optional `spec.lock.yaml`.
  - `lock.py` — `SpecLock` dataclass with SHA-256 source/spec hashing, staleness detection, YAML serialization. `create_lock()` factory function.
- **6 Jinja2 templates** (`templates/`): `requirements.md.j2`, `design.md.j2`, `tasks.md.j2`, `acceptance.yaml.j2`, `context.md.j2`, `sources.md.j2`.

#### Phase 4 — Verify (acceptance check engine)

- **Verification engine** (`verify/engine.py`): Runs acceptance.yaml checks against a project directory. Four check types: `command` (shell exit code), `files_exist` (path checks), `pattern_present` (regex in files), `pattern_absent` (forbidden patterns). Tag-based filtering, fail-fast mode, configurable timeout per check. `VerifyError` exception with reason + suggestion.
- **Report formatters** (`verify/reporter.py`):
  - `TerminalReporter` — Rich table with colors, pass/fail status, duration, details.
  - `JsonReporter` — Machine-readable JSON output.
  - `JunitReporter` — JUnit XML for CI integration (GitHub Actions, Jenkins, etc.).
  - `Reporter` Protocol with `@runtime_checkable` for extensibility.

#### Phase 5 — Export (agent-ready output)

- **Exporter framework** (`export/`):
  - `base.py` — `Exporter` Protocol with `@runtime_checkable` for structural subtyping.
  - `registry.py` — `ExporterRegistry` with format-based dispatch. Factory function `create_default_registry()` registers both built-in exporters.
- **Architect exporter** (`export/architect.py`): Generates `pipeline.yaml` with one step per task, checkpoint flags, project context injection, final verification step with required command checks. Copies all spec files to `output/spec/`.
- **Generic exporter** (`export/generic.py`): Generates `SPEC.md` (consolidated Markdown with all spec sections), `verify.sh` (executable bash script with `check()` helper, `set -euo pipefail`, exit code reporting). Copies all spec files to `output/spec/`.

#### Spec differ

- **Diff module** (`diff/differ.py`): Compares two spec versions by extracting sections from Markdown headings (FR/NFR IDs, task numbers) and acceptance check IDs. Reports added, removed, and modified items per section. `SpecDiff` dataclass with `added`, `removed`, `modified`, `has_changes` properties. `DiffError` exception.

#### CLI — Full pipeline wiring

- **`intake init`**: End-to-end pipeline: ingest → analyze → generate → (optional) export. Auto-detects tech stack, slugifies description for directory name, `--dry-run` support.
- **`intake add`**: Incremental source addition to existing spec. Parses new sources, re-analyzes, regenerates spec files.
- **`intake verify`**: Loads `acceptance.yaml`, runs checks via `VerificationEngine`, displays report in chosen format (terminal/json/junit), exits with semantic code (0/1/2).
- **`intake export`**: Exports spec to chosen format via `ExporterRegistry`.
- **`intake show`**: Displays spec summary from `spec.lock.yaml` (model, cost, counts) and file listing.
- **`intake list`**: Scans specs directory for valid spec subdirectories, shows table with metadata from lock files.
- **`intake diff`**: Compares two spec directories, shows Rich table with added/removed/modified items.

#### Test suite

- **313 tests**, **83% overall coverage**. 7 realistic fixture files (Markdown, plaintext, YAML, Jira JSON x2, Confluence HTML, PNG image).

#### Documentation and examples

- **`.intake.yaml.example`**: Fully documented configuration example with all options and defaults.
- **4 example projects** in `examples/`: `from-markdown`, `from-jira`, `from-scratch`, `multi-source` — each with README and realistic source files.

#### Error hardening

- **`EmptySourceError`** and **`FileTooLargeError`** exceptions for better error messages on edge cases.
- **`validate_file_readable()`** and **`read_text_safe()`** utilities — centralized file validation with UTF-8 → latin-1 encoding fallback, size limits (50MB), and empty file detection.
- All 8 parsers updated to use hardened file validation utilities.
- 16 new hardening tests covering empty files, encoding fallback, size limits, and directory rejection.

#### Doctor --fix

- **`intake doctor --fix`** command: auto-installs missing Python packages and creates default `.intake.yaml` configuration.
- `FixResult` dataclass for structured fix result reporting.
- `_find_pip()` detects `pip3.12`, `pip3`, or `pip` for package installation.
- `IMPORT_TO_PIP` mapping for correct PyPI package names (e.g., `bs4` → `beautifulsoup4`, `docx` → `python-docx`).

#### Code quality

- **0 ruff errors**: Fixed 88 lint issues (TC001/TC003, F401, I001, SIM103, RUF022, E501, SIM117, RUF043).
- **0 mypy --strict errors**: Fixed 26 type errors across 12 files. Proper isinstance narrowing, type-safe dict extraction, correct bool return types.

### Fixed

- **structlog test isolation**: Replaced `StringIO` sink with persistent `_NullWriter` class and yield-based autouse fixture. Fixed `cache_logger_on_first_use=True` in `setup_logging()` that caused "I/O operation on closed file" errors when CLI tests ran before module tests.
- **`_get_list` type safety**: Split into `_get_list` (for dict lists) and `_get_str_list` (for string lists) to fix mypy --strict without breaking acceptance criteria extraction.
- **bs4 `find()` kwargs**: Changed `**selector` to `attrs=selector` in Confluence parser for correct BeautifulSoup4 type narrowing.

