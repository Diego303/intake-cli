# intake

> From requirements in any format to verified implementation.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**intake** is an open-source CLI tool that acts as a universal bridge between real-world requirements and AI coding agents. It accepts requirements from multiple sources and formats — Jira exports, Confluence pages, PDFs, Markdown, YAML, images, DOCX, free text — and transforms them into a normalized, verifiable spec that any AI agent can consume.

It's not an IDE. It's not an agent. It doesn't generate code. intake is **preparation infrastructure**: the missing step between "we have some requirements somewhere" and "an agent implements with automatic verification."

```
intake = Chaotic requirements (N sources, N formats) → Executable spec → Any AI agent
```

---

## How It Works

```
INGEST (parsers) → ANALYZE (LLM) → GENERATE (spec files) → VERIFY (acceptance checks) → EXPORT (agent-ready output)
```

intake processes requirements through a 5-phase pipeline:

1. **Ingest** — Parse any input format into normalized `ParsedContent`
2. **Analyze** — LLM extracts structured requirements, detects conflicts, deduplicates
3. **Generate** — Produce 6 spec files + `spec.lock.yaml`
4. **Verify** — Run executable acceptance checks against the implementation
5. **Export** — Generate agent-ready output (Claude Code, Cursor, Kiro, Copilot, architect, generic)

### The 6 Spec Files

| File | Purpose |
|------|---------|
| `requirements.md` | What to build. Functional and non-functional requirements in EARS format. |
| `design.md` | How to build it. Architecture, interfaces, technical decisions. |
| `tasks.md` | In what order. Atomic tasks with dependencies. |
| `acceptance.yaml` | How to verify. Executable checks: commands, patterns, file existence. |
| `context.md` | Project context for the agent: stack, conventions, current state. |
| `sources.md` | Full traceability: every requirement mapped to its original source. |

---

## Installation

```bash
pip install intake-ai-cli
```

Requires Python 3.12+. The CLI command is `intake`.

### Development Setup

```bash
git clone https://github.com/your-org/intake-cli.git
cd intake-cli
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Check your environment
intake doctor

# Generate a spec from a single source
intake init "OAuth2 authentication system" -s requirements.md

# Generate from multiple sources
intake init "Payments feature" -s jira.json -s confluence.html -s notes.md

# Use a preset for quick configuration
intake init "API gateway" -s reqs.yaml --preset enterprise

# Export for a specific agent
intake init "User endpoint" -s reqs.pdf --format architect

# Quick mode for simple tasks (only context.md + tasks.md)
intake init "Fix login bug" -s notes.txt --mode quick

# Fetch requirements from a URL
intake init "API review" -s https://wiki.company.com/rfc/auth

# Fetch from live APIs (requires credentials)
intake init "Sprint planning" -s jira://PROJ/sprint/42
intake init "Wiki review" -s confluence://SPACE/Page-Title
intake init "Bug triage" -s github://org/repo/issues?labels=bug

# Export for specific agents
intake init "Payments" -s reqs.pdf --format claude-code
intake export ./specs/auth -f cursor -o .
intake export ./specs/auth -f kiro -o .
intake export ./specs/auth -f copilot -o .

# Analyze verification failures and get fix suggestions
intake feedback ./specs/auth-oauth2
intake feedback ./specs/auth -r report.json --apply --agent-format claude-code

# List discovered plugins
intake plugins list

# Track task progress
intake task list ./specs/auth-oauth2
intake task update ./specs/auth-oauth2 1 done --note "Implemented and tested"
```

---

## Supported Input Formats

| Format | Extensions / Source | Parser |
|--------|-----------|--------|
| Markdown | `.md` | Front matter, heading-based sections |
| Plain text | `.txt`, stdin (`-`) | Paragraph sections, Slack dumps |
| YAML / JSON | `.yaml`, `.yml`, `.json` | Structured requirements |
| PDF | `.pdf` | Text + tables via pdfplumber |
| DOCX | `.docx` | Text, tables, headings, metadata via python-docx |
| Jira export | `.json` (auto-detected) | Issues, comments, links, priorities |
| Confluence export | `.html` (auto-detected) | Clean Markdown via BS4 + markdownify |
| Images | `.png`, `.jpg`, `.webp`, `.gif` | LLM vision analysis |
| URLs | `http://`, `https://` | Fetches page, converts HTML → Markdown |
| Slack export | `.json` (auto-detected) | Messages, threads, decisions, action items |
| GitHub Issues | `.json` (auto-detected) | Issues, labels, comments, cross-references |
| **Jira API** | `jira://PROJ-123` | Live issue fetching via REST API |
| **Confluence API** | `confluence://SPACE/Title` | Live page fetching via REST API |
| **GitHub API** | `github://org/repo/issues/42` | Live issue fetching via PyGithub |

Format is auto-detected by file extension and content inspection. Jira, Slack, and GitHub Issues JSON exports are distinguished automatically from generic JSON files. Confluence HTML is distinguished from generic HTML.

### Live API Connectors

Connect directly to project management tools (requires credentials):

```bash
# Jira: single issue, multiple, JQL, sprint
intake init "Sprint" -s jira://PROJ-123
intake init "Sprint" -s "jira://PROJ?jql=sprint=42"

# Confluence: page by ID, by space/title, CQL search
intake init "Docs" -s confluence://page/123456
intake init "Docs" -s confluence://SPACE/Page-Title

# GitHub: single/multiple issues, filtered queries
intake init "Bugs" -s github://org/repo/issues/42
intake init "Bugs" -s "github://org/repo/issues?labels=bug&state=open"
```

Configure credentials in `.intake.yaml`:

```yaml
connectors:
  jira:
    url: https://your-org.atlassian.net
    # Set JIRA_API_TOKEN and JIRA_EMAIL env vars
  confluence:
    url: https://your-org.atlassian.net/wiki
    # Set CONFLUENCE_API_TOKEN and CONFLUENCE_EMAIL env vars
  github:
    # Set GITHUB_TOKEN env var
```

---

## Commands

| Command | Description | Status |
|---------|-------------|--------|
| `intake init` | Generate a spec from requirement sources | **Available** |
| `intake add` | Add sources to an existing spec (incremental) | **Available** |
| `intake verify` | Verify implementation against the spec | **Available** |
| `intake export` | Export spec to agent-ready format | **Available** |
| `intake show` | Show spec summary | **Available** |
| `intake list` | List all specs in the project | **Available** |
| `intake diff` | Compare two spec versions | **Available** |
| `intake doctor` | Check environment and configuration health | **Available** |
| `intake doctor --fix` | Auto-fix environment issues (install deps, create config) | **Available** |
| `intake feedback` | Analyze verification failures and suggest fixes | **Available** |
| `intake feedback --apply` | Auto-apply suggested spec amendments | **Available** |
| `intake plugins list` | List all discovered plugins (parsers, exporters, connectors) | **Available** |
| `intake plugins check` | Validate plugin compatibility | **Available** |
| `intake task list` | List tasks from a spec with current status | **Available** |
| `intake task update` | Update a task's status (pending/in_progress/done/blocked) | **Available** |

---

## Configuration

intake works with zero configuration — only an LLM API key is needed. For customization, create a `.intake.yaml`:

```yaml
llm:
  model: claude-sonnet-4
  max_cost_per_spec: 0.50
  temperature: 0.2

project:
  name: my-project
  language: en

spec:
  output_dir: ./specs
  requirements_format: ears    # ears | user-stories | bdd | free
  design_depth: moderate       # minimal | moderate | detailed
  task_granularity: medium     # coarse | medium | fine
  risk_assessment: true
  auto_mode: true              # auto-detect quick/standard/enterprise

export:
  default_format: generic      # architect | claude-code | cursor | kiro | copilot | generic

feedback:
  auto_amend_spec: false       # Auto-apply spec amendments from feedback
  max_suggestions: 10          # Max suggestions per analysis
  include_code_snippets: true  # Include code examples in suggestions

connectors:
  jira:
    url: https://your-org.atlassian.net
  confluence:
    url: https://your-org.atlassian.net/wiki
  github: {}                   # Uses GITHUB_TOKEN env var
```

### Presets

Skip the config file and use a preset:

```bash
intake init "My feature" -s reqs.md --preset minimal      # Fast, cheap, prototyping
intake init "My feature" -s reqs.md --preset standard      # Balanced (default)
intake init "My feature" -s reqs.md --preset enterprise    # Detailed, full traceability
```

### Configuration Priority

```
CLI flags > .intake.yaml > preset > hardcoded defaults
```

---

## Examples

See the [`examples/`](examples/) directory for ready-to-run scenarios:

| Example | Description |
|---------|-------------|
| [`from-markdown`](examples/from-markdown/) | Single Markdown file with OAuth2 requirements |
| [`from-jira`](examples/from-jira/) | Jira JSON export with 3 issues |
| [`from-scratch`](examples/from-scratch/) | Free-text meeting notes |
| [`multi-source`](examples/multi-source/) | Combining Markdown + Jira JSON + text notes |

---

## Architecture

```
src/intake/
├── cli.py                  # Click CLI — thin adapter, no logic
├── config/                 # Pydantic v2 models, presets, layered loader
│   ├── schema.py           #   9 config models (LLM, Project, Spec, Verification, Export, Security, Connectors, Feedback)
│   ├── presets.py           #   minimal / standard / enterprise presets
│   ├── loader.py            #   Layered merge: defaults → preset → YAML → CLI
│   └── defaults.py          #   Centralized constants
├── plugins/                # Plugin system (v0.2.0)
│   ├── protocols.py         #   V2 protocols: ParserPlugin, ExporterPlugin, ConnectorPlugin
│   ├── discovery.py         #   Entry point scanning via importlib.metadata
│   └── hooks.py             #   Pipeline hook system (HookManager)
├── connectors/             # Live API connectors
│   ├── base.py              #   ConnectorRegistry, ConnectorError
│   ├── jira_api.py          #   Jira REST API (single/multi/JQL/sprint)
│   ├── confluence_api.py    #   Confluence REST API (page/space/CQL)
│   └── github_api.py        #   GitHub API via PyGithub (issues/filters)
├── ingest/                 # Phase 1 — 11 parsers, registry, auto-detection
│   ├── base.py              #   ParsedContent dataclass + Parser Protocol
│   ├── registry.py          #   Auto-detection + plugin discovery + parser dispatch
│   ├── markdown.py          #   .md with YAML front matter
│   ├── plaintext.py         #   .txt, stdin, Slack dumps
│   ├── yaml_input.py        #   .yaml/.yml/.json structured input
│   ├── pdf.py               #   .pdf via pdfplumber
│   ├── docx.py              #   .docx via python-docx
│   ├── jira.py              #   Jira JSON exports (API + list format)
│   ├── confluence.py        #   Confluence HTML via BS4 + markdownify
│   ├── image.py             #   Image analysis via LLM vision
│   ├── url.py               #   HTTP/HTTPS URLs via httpx + markdownify
│   ├── slack.py             #   Slack workspace export JSON
│   └── github_issues.py     #   GitHub Issues JSON
├── analyze/                # Phase 2 — LLM orchestration (async)
│   ├── analyzer.py          #   Orchestrator: extraction → dedup → risk → design
│   ├── prompts.py           #   3 system prompts (extraction, risk, design)
│   ├── models.py            #   10 dataclasses for analysis pipeline
│   ├── complexity.py        #   Heuristic complexity classification (quick/standard/enterprise)
│   ├── extraction.py        #   LLM JSON → typed AnalysisResult
│   ├── dedup.py             #   Jaccard word similarity deduplication
│   ├── conflicts.py         #   Conflict validation
│   ├── questions.py         #   Open question validation
│   ├── risks.py             #   Risk assessment parsing
│   └── design.py            #   Design output parsing (tasks, checks)
├── generate/               # Phase 3 — Jinja2 template rendering
│   ├── spec_builder.py      #   Orchestrates 6 spec files + lock
│   ├── adaptive.py          #   AdaptiveSpecBuilder — mode-aware file selection
│   └── lock.py              #   spec.lock.yaml for reproducibility
├── verify/                 # Phase 4 — Acceptance check engine
│   ├── engine.py           #   4 check types: command, files_exist, pattern_*
│   └── reporter.py         #   Terminal (Rich), JSON, JUnit XML reporters
├── export/                 # Phase 5 — Agent-ready output (6 exporters)
│   ├── base.py             #   Exporter Protocol
│   ├── registry.py         #   Plugin discovery + format-based dispatch
│   ├── _helpers.py         #   Shared utilities (parse_tasks, load_checks, etc.)
│   ├── claude_code.py      #   CLAUDE.md + tasks + verify.sh
│   ├── cursor.py           #   .cursor/rules/intake-spec.mdc
│   ├── kiro.py             #   Kiro-native requirements/design/tasks
│   ├── copilot.py          #   .github/copilot-instructions.md
│   ├── architect.py        #   pipeline.yaml generation
│   └── generic.py          #   SPEC.md + verify.sh generation
├── diff/                   # Spec comparison
│   └── differ.py           #   Compare two specs by requirement/task IDs
├── feedback/               # Feedback loop (analyze failures, suggest fixes)
│   ├── analyzer.py         #   LLM-based failure analysis
│   ├── prompts.py          #   Feedback analysis prompt
│   ├── suggestions.py     #   Multi-format suggestion formatter
│   └── spec_updater.py    #   Preview + apply spec amendments
├── doctor/                 # Environment health checks
│   └── checks.py            #   Python, API keys, deps, connectors, config validation
├── llm/                    # LiteLLM wrapper (used by analyze/ only)
│   └── adapter.py           #   Async completion, retry, cost tracking, budget
├── templates/              # Jinja2 templates (15 total)
│   ├── requirements.md.j2   #   FR, NFR, conflicts, open questions
│   ├── design.md.j2         #   Components, files, tech decisions
│   ├── tasks.md.j2          #   Task summary + status + detailed sections
│   ├── acceptance.yaml.j2   #   Executable acceptance checks
│   ├── context.md.j2        #   Project context for agents
│   ├── sources.md.j2        #   Source traceability mapping
│   ├── claude_md.j2         #   Claude Code CLAUDE.md spec section
│   ├── claude_task.md.j2    #   Claude Code per-task file
│   ├── verify_sh.j2         #   Claude Code verification script
│   ├── cursor_rules.mdc.j2  #   Cursor rules file
│   ├── kiro_*.md.j2         #   Kiro requirements/design/tasks (3 files)
│   ├── copilot_instructions.md.j2  # Copilot instructions
│   └── feedback.md.j2      #   Feedback results template
└── utils/                  # Shared utilities
    ├── file_detect.py       #   Extension-based format detection
    ├── project_detect.py    #   Auto-detect tech stack from project files
    ├── source_uri.py        #   URI parsing (jira://, github://, http://, files, text)
    ├── task_state.py         #   Task status tracking in tasks.md
    ├── cost.py              #   Cost accumulation with per-phase breakdown
    └── logging.py           #   structlog configuration
```

**Key design principles:**

- **Protocol over ABC** — All extension points use `typing.Protocol`
- **Plugin-first architecture** — Parsers, exporters, and connectors discovered via entry points, manual fallback
- **Dataclasses for pipeline data, Pydantic for config** — Never mixed
- **Async only in analyze/** — Everything else is synchronous
- **Offline mode** — Parsing, verification, export, diff, doctor all work without LLM
- **Adaptive generation** — Complexity auto-detection selects quick/standard/enterprise mode
- **No magic strings** — All constants defined explicitly
- **Budget enforcement** — LLM cost tracked per call with configurable limits

---

## Integration

### With architect

```bash
intake init "Auth system" -s reqs.md --format architect
architect pipeline specs/auth-system/pipeline.yaml
```

### With Claude Code

```bash
intake init "Payments" -s reqs.pdf --format claude-code
# Generates CLAUDE.md + .intake/tasks/ + .intake/verify.sh + .intake/spec-summary.md
```

### With Cursor

```bash
intake export ./specs/auth -f cursor -o .
# Generates .cursor/rules/intake-spec.mdc (auto-loaded by Cursor)
```

### With Kiro

```bash
intake export ./specs/auth -f kiro -o .
# Generates requirements.md, design.md, tasks.md in Kiro native format
```

### With GitHub Copilot

```bash
intake export ./specs/auth -f copilot -o .
# Generates .github/copilot-instructions.md (auto-loaded by Copilot)
```

### Feedback Loop

```bash
# Analyze why verification checks failed and get fix suggestions
intake feedback ./specs/auth-oauth2

# Use a previous report and auto-apply spec amendments
intake feedback ./specs/auth -r report.json --apply

# Get suggestions formatted for your agent
intake feedback ./specs/auth --agent-format claude-code
```

### With CI/CD

```yaml
# GitHub Actions
- name: Verify spec compliance
  run: |
    pip install intake-ai-cli
    intake verify specs/auth-system/ -p . --format junit
```

---

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=intake --cov-report=term-missing

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check (strict)
mypy src/ --strict
```

Current test suite: **673 tests**, **0 mypy --strict errors**, **0 ruff warnings**.

### Implementation Status

| Phase | Module | Status |
|-------|--------|--------|
| Phase 1 — Ingest | `ingest/` (11 parsers + plugin-based registry) | Implemented |
| Phase 2 — Analyze | `analyze/` (orchestrator + 7 sub-modules + complexity) | Implemented |
| Phase 3 — Generate | `generate/` (spec builder + adaptive builder + 6 templates + lock) | Implemented |
| Phase 4 — Verify | `verify/` (engine + 3 reporters) | Implemented |
| Phase 5 — Export | `export/` (6 exporters: claude-code, cursor, kiro, copilot, architect, generic) | Implemented |
| Plugins | `plugins/` (protocols + discovery + hooks) | Implemented |
| Connectors | `connectors/` (Jira, Confluence, GitHub API connectors) | Implemented |
| Feedback | `feedback/` (analyzer + suggestions + spec updater) | Implemented |
| Standalone | `doctor/`, `config/`, `llm/`, `utils/` | Implemented |
| Standalone | `diff/` (spec differ) | Implemented |
| CLI | 15 commands/subcommands wired end-to-end | Implemented |

---

## Model Support

intake uses [LiteLLM](https://github.com/BerriAI/litellm) for LLM abstraction, supporting 100+ models:

- **Anthropic**: Claude Sonnet, Claude Opus, Claude Haiku
- **OpenAI**: GPT-4o, GPT-4, GPT-3.5
- **Google**: Gemini Pro, Gemini Flash
- **Local models**: Ollama, vLLM, etc.

Set your API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

---

## License

MIT
