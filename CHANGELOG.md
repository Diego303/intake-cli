# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-03-07

### Added

#### GitLab API connector

- **GitLab connector** (`connectors/gitlab_api.py`): Fetches issues from GitLab via python-gitlab v8.x. Supports single issue (`gitlab://group/project/issues/42`), multiple issues (`gitlab://group/project/issues/42,43`), filtered queries (`gitlab://group/project/issues?labels=bug&state=opened`), and milestone-based fetching (`gitlab://group/project/milestones/3/issues`). Nested group support (`gitlab://org/team/subgroup/project/issues/10`). Lazy import with clear `ImportError`. Configurable SSL verification for self-hosted instances.
- **GitlabConfig** (`config/schema.py`): `url`, `token_env`, `auth_type`, `default_project`, `include_comments`, `include_merge_requests`, `max_notes`, `ssl_verify`.
- **Doctor check**: `GITLAB_TOKEN` credential validation when GitLab connector is configured.
- **Entry point** in `pyproject.toml`: `gitlab` under `[project.entry-points."intake.connectors"]`.

#### GitLab Issues parser

- **GitlabIssuesParser** (`ingest/gitlab_issues.py`): Parses GitLab Issues JSON (single object, array, or wrapped `{"issues": [...]}` format). Extracts titles, descriptions, labels, milestones, weights, assignees, discussion notes (truncated to 500 chars), and linked merge requests. Detects `#NNN` and `!NNN` cross-references as relations.
- **JSON subtype detection** (`ingest/registry.py`): `iid` field detection for GitLab Issues (after Jira, before GitHub Issues in priority order).
- **Entry point** in `pyproject.toml`: `gitlab_issues` under `[project.entry-points."intake.parsers"]`.

#### Spec validator (`intake validate`)

- **SpecValidator** (`validate/checker.py`): Offline spec quality gate with 5 check categories: structure (required files, YAML validity), cross_reference (requirements referenced in tasks, tasks in acceptance), consistency (task dependency cycles via DFS, duplicate IDs), acceptance (valid check types, required fields), completeness (orphaned requirements, tasks without acceptance checks). Compiled regex patterns as module constants.
- **ValidateConfig** (`config/schema.py`): `strict` (treat warnings as errors), `required_sections`, `max_orphaned_requirements`.
- **`intake validate`** CLI command with `--strict` and `--preset` options.

#### Cost estimator (`intake estimate`)

- **CostEstimator** (`estimate/estimator.py`): LLM cost estimation with 7-model pricing table (Claude Sonnet/Opus, GPT-4o/4o-mini/4-turbo, Gemini Flash/Pro). Supports `estimate_from_files()` and `estimate_from_sources()`. Three modes (quick/standard/enterprise) with different call multipliers. Budget warnings when estimated cost exceeds `max_cost_per_spec`. `TYPE_CHECKING` guard for `ParsedContent` import.
- **EstimateConfig** (`config/schema.py`): `tokens_per_word`, `prompt_overhead_tokens`, `calls_per_mode`.
- **`intake estimate`** CLI command with `--model` and `--mode` options.

#### Custom template loading

- **TemplateLoader** (`templates/loader.py`): Jinja2 `ChoiceLoader` that prioritizes user templates (configurable directory) over built-in `PackageLoader` templates. Lazy environment creation. Override detection with optional warning log.
- **TemplatesConfig** (`config/schema.py`): `user_dir` (default: `.intake/templates`), `warn_on_override`.

#### CI export (`intake export-ci`)

- **`intake export-ci`** CLI command: Generates CI/CD pipeline configuration files. `--platform gitlab` generates `.gitlab-ci.yml`, `--platform github` generates `.github/workflows/intake-verify.yml`. Customizable output path with `--output`.
- **`gitlab_ci.yml.j2`** template: GitLab CI pipeline with verify + report stages.
- **`github_actions.yml.j2`** template: GitHub Actions workflow for spec verification.

#### MCP tools (2 new, 9 total)

- **`intake_validate`** MCP tool: Run offline spec validation via MCP. Uses `ValidateConfig` and `SpecValidator`.
- **`intake_estimate`** MCP tool: Estimate LLM cost for a spec via MCP. Scans `.md`/`.yaml`/`.yml` files in the spec directory.

#### Configuration

- **GitlabConfig** added to `ConnectorsConfig`.
- **ValidateConfig** added to `IntakeConfig` as `validate_spec` (alias `"validate"`).
- **EstimateConfig** added to `IntakeConfig`.
- **TemplatesConfig** added to `IntakeConfig`.

#### Examples

- **`examples/from-gitlab/`** (NEW): GitLab API connector walkthrough with URI format reference, self-hosted configuration, and troubleshooting guide. Includes sample `gitlab-issues.json` with 2 issues.

#### Test suite

- **882 tests** (up from 775), **0 failures**, **10 skipped**. 107 new tests added.
- 5 new test files: `test_validate/test_checker.py` (24), `test_estimate/test_estimator.py` (24), `test_ingest/test_gitlab_issues.py` (19), `test_connectors/test_gitlab_api.py` (26), `test_templates/test_loader.py` (14).
- 1 new fixture file: `tests/fixtures/gitlab_issues.json` (2 GitLab issues with notes, labels, MRs).

### Fixed

- **`gitlab://` URI routing** (`cli.py`): Added `"gitlab"` to connector routing tuple — previously `gitlab://` URIs were silently ignored.
- **GitLab config injection** (`cli.py`): Added `"gitlab": config.connectors.gitlab` to config map — previously GitLab connector had no config.
- **MCP tools docstring** (`mcp/tools.py`): Updated from "7 tools" to "9 tools" to reflect actual count.

## [0.5.0] - 2026-03-07

### Added

#### GitHub Actions action

- **`action/action.yml`** (NEW): Composite GitHub Action for verifying spec compliance in CI/CD. Inputs: `spec-dir`, `project-dir`, `report-format` (terminal/json/junit), `report-output`, `tags`, `fail-fast`, `python-version`, `intake-version`. Outputs: `result`, `total-checks`, `passed-checks`, `failed-checks`, `report-path`. Automatically uploads report as artifact.

#### CI pipeline

- **`.github/workflows/ci.yml`** (NEW): Full CI pipeline with 4 jobs: lint (ruff check + format), typecheck (mypy strict), test (Python 3.12 + 3.13 with coverage), build (package + verify install). Runs on push to main/develop and PRs to main. Concurrency groups cancel in-progress runs.

#### Examples

- **`examples/from-jira-api/`** (NEW): Live Jira API connector walkthrough with URI format reference and troubleshooting.
- **`examples/mcp-session/`** (NEW): MCP server setup guide for Claude Code, Cursor, and SSE transport. Tool/resource/prompt reference. Complete implementation walkthrough.
- **`examples/feedback-loop/`** (NEW): Verify-feedback-fix cycle documentation with failure types, auto-apply amendments, and watch mode integration.
- **`examples/quick-mode/`** (NEW): Quick mode usage for simple tasks with auto-detection rules and output comparison.
- **`examples/plugin-custom-parser/`** (NEW): Complete plugin development guide covering parser, exporter, and connector creation with V1 vs V2 protocol reference.

#### Documentation

- **README.md** updated with MCP setup guides (Claude Code `.mcp.json`, Cursor settings, SSE), GitHub Action usage, plugin development section, 9 examples table.
- **`.intake.yaml.example`** updated with ALL configuration fields: connectors (jira/confluence/github), feedback, mcp, watch sections with full documentation.

#### Test suite

- **775 tests** (up from 772), **0 failures**, **10 skipped** (MCP prompts tests when mcp package not installed). 3 new tests for connector temp file error handling.

### Fixed

#### mypy strict compliance

- **0 mypy --strict errors** (down from 39): Added `[[tool.mypy.overrides]]` for optional dependencies without type stubs (mcp, atlassian, github, uvicorn, starlette, watchfiles). Fixed `type: ignore` comments in MCP modules (tools, resources, prompts, server) to use correct error codes (`attr-defined`, `untyped-decorator`). Changed `create_server()` return type from `object` to `Any`. Removed stale `type: ignore[arg-type]` comments on Starlette Route calls.

#### Error handling hardening

- **Feedback command** (`cli.py`): Added specific `FileNotFoundError` check for verify report file with actionable hint. Added `json.JSONDecodeError` handling with suggestion to regenerate report.
- **Connector fetch** (`cli.py`): Added `TimeoutError` and `OSError` handling in `_fetch_connector_source` for graceful degradation on network failures with actionable hints.
- **Connector temp files** (`connectors/`): All 3 connectors (Jira, Confluence, GitHub) now wrap temp file creation in `try/except OSError` and raise `ConnectorError` with disk space suggestion.
- **Verify engine** (`verify/engine.py`): Added `logger.warning` for `OSError` when reading files during pattern checks instead of silently continuing.

## [0.4.0] - 2026-03-05

### Added

#### MCP (Model Context Protocol) server

- **MCP server module** (`mcp/`): Full MCP server implementation with stdio and SSE transports. Requires `pip install intake-ai-cli[mcp]`.
- **`create_server()`** (`mcp/server.py`): Creates and configures the MCP server with all tools, resources, and prompts registered. `MCP_SERVER_NAME = "intake-spec"`.
- **`run_stdio()`** and **`run_sse()`** (`mcp/server.py`): Two transport modes — stdio for CLI agent integration, SSE (HTTP) for browser/IDE integration via starlette + uvicorn.
- **7 MCP tools** (`mcp/tools.py`):
  - `intake_show`: Show spec summary with truncated file content (MAX_SECTION_LENGTH = 3000).
  - `intake_get_context`: Read `context.md` for a spec.
  - `intake_get_tasks`: List tasks with status filtering (all/pending/in_progress/done/blocked).
  - `intake_update_task`: Update task status with optional note.
  - `intake_verify`: Run acceptance checks with optional tag filtering.
  - `intake_feedback`: Run verification + analyze failures.
  - `intake_list_specs`: List available specs (filters directories without `requirements.md`).
- **MCP resources** (`mcp/resources.py`): Dynamic spec file resources via `intake://specs/{name}/{section}` URIs. Supports 6 sections: requirements, tasks, context, acceptance, design, sources. `FILE_MAP` maps section names to actual filenames.
- **MCP prompts** (`mcp/prompts.py`): Two structured prompt templates:
  - `implement_next_task`: Reads spec files and generates implementation instructions referencing MCP tools.
  - `verify_and_fix`: Generates a verify → fix → re-verify loop until all checks pass.
- **MCPError exception** (`mcp/__init__.py`): Error with `reason` and `suggestion` attributes.
- **Lazy imports**: `mcp`, `starlette`, `uvicorn` imported lazily with clear `ImportError` messages and installation commands.

#### Watch mode (file monitoring + auto-verification)

- **Watch module** (`watch/`): File watcher with selective re-verification. Requires `pip install intake-ai-cli[watch]`.
- **SpecWatcher** (`watch/watcher.py`): Monitors project directory using `watchfiles` (Rust-based, efficient). On file change, re-runs verification checks and displays results.
  - `run_once()`: Single verification without watching.
  - `run()`: Continuous watch loop with debouncing.
  - `_filter_ignored()`: Filters files by ignore patterns (fnmatch per path component).
  - `_matches_any()`: Static method for pattern matching against individual path components.
  - `_extract_changed_files()`: Extracts relative paths from watchfiles change sets.
  - `MAX_CHANGED_FILES_DISPLAY = 5`: Limits terminal output.
- **WatchError exception** (`watch/__init__.py`): Error with `reason` and `suggestion` attributes.
- **Debouncing**: Configurable via `WatchConfig.debounce_seconds`, passed to watchfiles native debouncing.

#### Configuration

- **MCPConfig** (`config/schema.py`): `specs_dir`, `project_dir`, `transport` (stdio/sse), `sse_port`.
- **WatchConfig** (`config/schema.py`): `debounce_seconds` (default: 2.0), `ignore_patterns` (default: `["*.pyc", "__pycache__", ".git", "node_modules", ".intake"]`).
- Both added to `IntakeConfig` as `mcp` and `watch` fields.

#### CLI commands

- **`intake mcp serve`**: Start the MCP server. Options: `--transport` (stdio/sse), `--port`, `--specs-dir`, `--project-dir`.
- **`intake watch`**: Watch project files and re-run verification. Options: `--project-dir`, `--tags`, `--debounce`, `--verbose`.

#### Optional dependencies

- `mcp = ["mcp[cli]>=1.0"]`: MCP server support.
- `watch = ["watchfiles>=1.0"]`: Watch mode support.
- `all = [connectors + watch + mcp]`: Install everything.

#### Test suite

- **772 tests** (up from 673), **0 failures**, **10 skipped** (MCP prompts tests when mcp package not installed). 99 new tests added.
- 5 new test files: `test_mcp/test_tools.py` (31), `test_mcp/test_resources.py` (17), `test_mcp/test_prompts.py` (10), `test_mcp/test_server.py` (10), `test_watch/test_watcher.py` (27).
- Config tests: 2 new tests for MCPConfig and WatchConfig nested overrides.
- CLI tests: 4 new tests for MCP and Watch help output.

### Fixed

- **`_filter_ignored` path matching** (`watch/watcher.py`): Fixed fnmatch to check individual path components (e.g., `.git` now correctly matches `.git/objects/abc`). Added `_matches_any()` static method.
- **Silent exception in `_handle_get_tasks`** (`mcp/tools.py`): Added `logger.debug("task_state_manager_fallback", ...)` to bare `except Exception` block.
- **Missing `run_sse` export** (`mcp/__init__.py`): Added `run_sse` to `__all__` and convenience re-export function.
- **`__all__` sort order** (`mcp/__init__.py`): Fixed RUF022 by sorting alphabetically.
- **ruff TC003 in tests**: Added `per-file-ignores` rule for `tests/**/*.py` to allow stdlib imports at runtime in test fixtures.

## [0.3.0] - 2026-03-04

### Added

#### 3 API connectors (live data fetching)

- **Jira connector** (`connectors/jira_api.py`): Fetches issues from Jira via REST API. Supports single issue (`jira://PROJ-123`), multiple issues (`jira://PROJ-1,PROJ-2`), JQL queries (`jira://PROJ?jql=sprint=42`), and sprint-based fetching (`jira://PROJ/sprint/42`). Lazy import of `atlassian-python-api`. Saves as JSON temp files compatible with `JiraParser`.
- **Confluence connector** (`connectors/confluence_api.py`): Fetches pages from Confluence Cloud/Server. Supports page by ID (`confluence://page/123456`), by space and title (`confluence://SPACE/Page-Title`), and CQL search (`confluence://search?cql=...`). Saves as HTML temp files compatible with `ConfluenceParser`.
- **GitHub connector** (`connectors/github_api.py`): Fetches issues from GitHub repos via PyGithub. Supports single issue (`github://org/repo/issues/42`), multiple issues, and filtered queries (`github://org/repo/issues?labels=bug&state=open`). Max 50 issues, 10 comments per issue.
- **Doctor connector checks** (`doctor/checks.py`): `_check_connectors()` validates connector credentials when connectors are configured.
- **3 connector entry points** in `pyproject.toml`: `jira`, `confluence`, `github` under `[project.entry-points."intake.connectors"]`.

#### 4 new exporters (6 total)

- **Claude Code exporter** (`export/claude_code.py`): Generates `CLAUDE.md` (smart append/replace), `.intake/tasks/TASK-NNN.md`, `.intake/verify.sh`, `.intake/spec-summary.md`, and `.intake/spec/` copy.
- **Cursor exporter** (`export/cursor.py`): Generates `.cursor/rules/intake-spec.mdc` with YAML frontmatter.
- **Kiro exporter** (`export/kiro.py`): Generates `requirements.md`, `design.md`, `tasks.md` in Kiro's native format.
- **Copilot exporter** (`export/copilot.py`): Generates `.github/copilot-instructions.md`.
- All 4 exporters implement the **V2 ExporterPlugin protocol**: `meta`, `supported_agents`, `export() → ExportResult`.
- **Shared export helpers** (`export/_helpers.py`): `read_spec_file()`, `parse_tasks()`, `load_acceptance_checks()`, `summarize_content()`, `count_requirements()`.
- **9 new Jinja2 templates**: `claude_md.j2`, `claude_task.md.j2`, `verify_sh.j2`, `cursor_rules.mdc.j2`, `kiro_requirements.md.j2`, `kiro_design.md.j2`, `kiro_tasks.md.j2`, `copilot_instructions.md.j2`, `feedback.md.j2`.

#### Feedback loop (analyze verification failures)

- **Feedback analyzer** (`feedback/analyzer.py`): LLM-based failure analysis with root cause identification, severity classification, and spec amendments. Dataclasses: `SpecAmendment`, `FailureAnalysis`, `FeedbackResult`.
- **Feedback prompts** (`feedback/prompts.py`): Analysis prompt with `{language}` placeholder and structured JSON output schema.
- **Suggestion formatter** (`feedback/suggestions.py`): Terminal output (Rich) + agent-specific formatting (generic, claude-code, cursor).
- **Spec updater** (`feedback/spec_updater.py`): Preview and apply spec amendments with add/modify/remove actions.
- **`intake feedback` CLI command**: Options `--verify-report`, `--project-dir`, `--apply`, `--agent-format`, `--verbose`.

#### Configuration updates

- **`FeedbackConfig`** model: `auto_amend_spec`, `max_suggestions`, `include_code_snippets`.
- **Expanded connector configs**: `JiraConfig` (auth_type, fields, max_comments), `ConfluenceConfig` (include_child_pages, max_depth), `GithubConfig` (default_repo).
- **`ExportConfig`** expanded: `claude_code_task_dir`, `cursor_rules_dir`.

#### Enterprise documentation

- **`docs/seguridad.md`** (NEW): Threat model, data flow, secrets management, redaction patterns, offline/air-gapped mode, audit trail, compliance (SOC2/HIPAA/ISO 27001/GDPR).
- **`docs/despliegue.md`** (NEW): Docker multi-stage, docker-compose, pre-commit hooks, deployment patterns, env vars.
- **`docs/integracion-cicd.md`** (NEW): GitHub Actions, GitLab CI, Jenkins, Azure DevOps, JUnit/JSON reports, spec drift, notifications.
- **`docs/flujos-trabajo.md`** (NEW): Solo developer, small team, enterprise, monorepo, AI agent, regulated industries.
- **`docs/conectores.md`** (NEW): Jira, Confluence, GitHub API connectors documentation.
- **`docs/feedback.md`** (NEW): Feedback loop usage, severity levels, spec amendments, agent formats.
- **`SECURITY.md`** (NEW): English security policy at project root (GitHub Security tab).
- 10 existing documentation files updated with Phase 2 content.

#### Test suite

- **673 tests** (up from 492), **0 failures**. 181 new tests added.
- 14 new test files covering connectors, exporters, feedback, and protocol conformance.
- Protocol conformance tests: 20 parametrized tests for V2 exporters + 3 for connectors.

### Fixed

#### QA Audit (14 mypy errors, 7 ruff errors, 25 format issues)

- **ExporterRegistry type safety** (`export/registry.py`): Introduced `AnyExporter = Exporter | Any` union type for V1/V2 dual protocol support. Changed `_exporters`, `register()`, and `get()` types to accept both V1 and V2 exporters without `type: ignore`.
- **Connector `Returning Any`** (`connectors/jira_api.py`, `connectors/confluence_api.py`): Wrapped `data.get()` calls with `list()` and explicit `str` annotations to satisfy mypy --strict.
- **Unused `type: ignore` comments**: Removed 3 stale `# type: ignore[import-untyped]` from connectors after `atlassian-python-api` and `PyGithub` gained type stubs.
- **CLI report type** (`cli.py`): Changed `report_data: dict[str, object]` to `dict[str, Any]` for correct iterable access.
- **Connector registration guard** (`cli.py`): Added `isinstance(connector_obj, ConnectorPlugin)` check for type-safe connector registration.
- **Unused imports** (`tests/`): Removed `PropertyMock`, `pytest`, `json`, `yaml` unused imports in test files.
- **TYPE_CHECKING import** (`tests/test_feedback/test_analyzer.py`): Moved `Path` import to `TYPE_CHECKING` block (TC003).
- **25 files reformatted** with `ruff format` for consistent code style.

## [0.2.0] - 2026-03-04

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

