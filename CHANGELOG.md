# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-03

### Added

#### Plugin system (extensible architecture)

- **Plugin protocols** (`plugins/protocols.py`): V2 extension contracts — `ParserPlugin`, `ExporterPlugin`, `ConnectorPlugin` protocols with `@runtime_checkable`. Supporting dataclasses: `PluginMeta`, `ExportResult`, `FetchedSource`. Exceptions: `PluginError`, `PluginLoadError`.
- **Plugin discovery** (`plugins/discovery.py`): Automatic plugin loading via `importlib.metadata.entry_points()` (PEP 621). `PluginRegistry` with `discover_all()`, `discover_group()`, `get_parsers()`, `get_exporters()`, `get_connectors()`, `list_plugins()`, `check_compatibility()`. Three entry point groups: `intake.parsers`, `intake.exporters`, `intake.connectors`.
- **Pipeline hooks** (`plugins/hooks.py`): `HookManager` with `register()`, `emit()`, `registered_events`. Callbacks are called in order; exceptions are caught and logged without blocking other callbacks. Ready for Phase 2 event wiring.
- **Entry points in `pyproject.toml`**: 11 parsers + 2 exporters registered as `[project.entry-points]`. All discoverable via `intake plugins list`.

#### Registry refactoring

- **Parser registry** (`ingest/registry.py`): `ParserRegistry` now accepts an optional `PluginRegistry` and attempts plugin-based discovery before falling back to manual registration. New `discover_parsers()` method. JSON subtype detection expanded: Jira → GitHub Issues → Slack → generic YAML.
- **Exporter registry** (`export/registry.py`): Same plugin-first pattern. `ExporterRegistry` with optional `PluginRegistry`, `discover_exporters()` method, plugin-first `create_default_registry()`.

#### 3 new parsers (11 total)

- **UrlParser** (`ingest/url.py`): Fetches HTTP/HTTPS URLs via `httpx` (sync), converts HTML to Markdown via BeautifulSoup4 + markdownify. Extracts page title, heading-based sections. Auto-detects source type (confluence, jira, github) from URL patterns. Handles connection errors, timeouts, and HTTP errors with user-friendly `ParseError`.
- **SlackParser** (`ingest/slack.py`): Parses Slack workspace export JSON format (array of message objects with `type`, `user`, `text`, `ts`, `thread_ts`, `reactions`). Groups messages by thread. Detects decisions via reactions (thumbsup, white_check_mark) and keywords. Detects action items via keywords (TODO, action item, etc.). Metadata: message_count, thread_count, decision_count, action_item_count.
- **GithubIssuesParser** (`ingest/github_issues.py`): Parses GitHub Issues JSON (single object or array). Extracts labels, assignees, milestones, state, html_url, comments. Detects `#NNN` cross-references as relations. Supports both array and single-issue formats.

#### Source URI parsing

- **Source URI parser** (`utils/source_uri.py`): `SourceURI` dataclass and `parse_source()` function. Detection order: stdin (`-`) → scheme URIs (`jira://`, `confluence://`, `github://`) → HTTP(S) URLs → existing files → file extensions → free text fallback. `SCHEME_PATTERNS` dict with compiled regexes.

#### Connector infrastructure

- **Connector base** (`connectors/base.py`): `ConnectorRegistry` with `register()`, `find_for_uri()`, async `fetch()`, `validate_all()`, `available_schemes`. Exceptions: `ConnectorError`, `ConnectorNotFoundError`. No concrete connectors yet (Phase 2).

#### Complexity classification and adaptive generation

- **Complexity classifier** (`analyze/complexity.py`): `ComplexityAssessment` dataclass and `classify_complexity()` function. Three modes: quick (<500 words, 1 source, no structure), standard (default), enterprise (4+ sources OR >5000 words). Heuristic-based, no LLM dependency.
- **Adaptive spec builder** (`generate/adaptive.py`): `GenerationPlan` dataclass and `AdaptiveSpecBuilder` class. Wraps standard `SpecBuilder` and filters files by mode: quick generates only `context.md` + `tasks.md`, standard generates all 6, enterprise generates all 6 with detailed risks. `create_generation_plan()` respects user config overrides.

#### Task state tracking

- **TaskStateManager** (`utils/task_state.py`): Reads and updates `tasks.md` in a spec directory. `list_tasks()` with optional status filter, `get_task()`, `update_task()` with persistence. Supports statuses: pending, in_progress, done, blocked. `TaskStatus` dataclass, `TaskStateError` exception.
- **TaskItem.status field** added to `analyze/models.py` (default: `"pending"`).
- **tasks.md.j2 template** updated with Status column in summary table and `**Status:**` field in detail sections.

#### New CLI commands

- **`intake plugins list`**: Shows table of all discovered plugins with name, group, version, V2 status, built-in status. Verbose mode (`-v`) adds module and error columns.
- **`intake plugins check`**: Validates compatibility of all discovered plugins. Reports OK or FAIL per plugin.
- **`intake task list <spec_dir>`**: Lists tasks from a spec with current status. Supports `--status` filter (repeatable). Shows progress summary.
- **`intake task update <spec_dir> <task_id> <status>`**: Updates task status in tasks.md. Supports `--note` for annotations.
- **`intake init --mode`**: New `--mode quick|standard|enterprise` option. When omitted and `spec.auto_mode` is True, auto-classifies complexity from sources.

#### init command enhancements

- Source URI resolution via `parse_source()` — detects file, URL, stdin, and scheme URIs.
- Scheme URIs (`jira://`, `confluence://`, `github://`) display "connector not available yet" warning.
- HTTP/HTTPS URLs routed to UrlParser automatically.
- Complexity classification + adaptive generation when `--mode` not specified.
- `AdaptiveSpecBuilder` replaces `SpecBuilder` for mode-aware file selection.

#### Configuration schema updates

- `SpecConfig.auto_mode: bool = True` — enables automatic complexity classification.
- `ConnectorsConfig` with `JiraConnectorConfig`, `ConfluenceConnectorConfig`, `GithubConnectorConfig` sub-models (Phase 2 preparation).
- `IntakeConfig.connectors` field added.

#### Optional dependencies in pyproject.toml

- `connectors = ["atlassian-python-api>=3.40", "PyGithub>=2.0"]`
- `watch = ["watchfiles>=0.21"]`
- `mcp = ["mcp>=1.0"]`
- `respx>=0.21` added to dev dependencies.

#### Test suite

- **492 tests** (up from 313), **0 failures**. 179 new tests added.
- 13 new test files: test_protocols, test_discovery, test_hooks, test_base (connectors), test_source_uri, test_task_state, test_url, test_slack, test_github_issues, test_complexity, test_adaptive.
- 3 new fixture files: `sample_webpage.html`, `slack_export.json`, `github_issues.json`.
- Plugin discovery tests added to `test_ingest/test_registry.py` and `test_export/test_registry.py`.
- CLI tests for plugins, task, and init --mode commands added to `test_cli.py`.

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

#### Documentation

- **`docs/` directory** fully updated with v0.2.0 content: architecture, pipeline, formats, CLI guide, configuration, best practices, troubleshooting.
- **`docs/plugins.md`** (NEW): Complete plugin system documentation — discovery mechanism, built-in plugins table, V1 vs V2 protocols, how to create external plugins, HookManager, PluginRegistry API.
- **`docs/github-notes/v0.2.0.md`** (NEW): Full release notes with highlights, migration guide, quality metrics.

### Fixed

- **structlog test isolation**: Replaced `StringIO` sink with persistent `_NullWriter` class and yield-based autouse fixture. Fixed `cache_logger_on_first_use=True` in `setup_logging()` that caused "I/O operation on closed file" errors when CLI tests ran before module tests.
- **`_get_list` type safety**: Split into `_get_list` (for dict lists) and `_get_str_list` (for string lists) to fix mypy --strict without breaking acceptance criteria extraction.
- **bs4 `find()` kwargs**: Changed `**selector` to `attrs=selector` in Confluence parser for correct BeautifulSoup4 type narrowing.

### QA Audit

Full QA audit completed with 105 issues found and resolved:

- **51 ruff lint errors** fixed: TC001 (8), RUF002 (2), N817 (2), E501 (4), F841 (2), TC003 (2), F401/I001 (30 auto-fixed), RUF100 (1).
- **54 ruff format issues** fixed: Auto-formatted with `ruff format`.
- **4 mypy --strict errors** fixed: `Returning Any` in `github_issues.py`, unused `type: ignore` in `discovery.py`, `list[object]` vs `list[ParsedContent]` in `cli.py`.
- **0 security issues**: No hardcoded credentials, no sensitive data in logs.
- **Coverage**: 86% overall (target: 65%). All modules above their individual targets.

