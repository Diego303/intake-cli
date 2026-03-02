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
5. **Export** — Generate agent-ready output (architect, Claude Code, Cursor, generic)

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
```

---

## Supported Input Formats

| Format | Extensions | Parser |
|--------|-----------|--------|
| Markdown | `.md` | Front matter, heading-based sections |
| Plain text | `.txt`, stdin (`-`) | Paragraph sections, Slack dumps |
| YAML / JSON | `.yaml`, `.yml`, `.json` | Structured requirements |
| PDF | `.pdf` | Text + tables via pdfplumber |
| DOCX | `.docx` | Text, tables, headings, metadata via python-docx |
| Jira export | `.json` (auto-detected) | Issues, comments, links, priorities |
| Confluence export | `.html` (auto-detected) | Clean Markdown via BS4 + markdownify |
| Images | `.png`, `.jpg`, `.webp`, `.gif` | LLM vision analysis |

Format is auto-detected by file extension and content inspection. Jira JSON exports and Confluence HTML exports are distinguished automatically from generic JSON/HTML files.

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

export:
  default_format: generic      # architect | claude-code | cursor | kiro | generic
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
│   ├── schema.py           #   6 config models (LLM, Project, Spec, Verification, Export, Security)
│   ├── presets.py           #   minimal / standard / enterprise presets
│   ├── loader.py            #   Layered merge: defaults → preset → YAML → CLI
│   └── defaults.py          #   Centralized constants
├── ingest/                 # Phase 1 — 8 parsers, registry, auto-detection
│   ├── base.py              #   ParsedContent dataclass + Parser Protocol
│   ├── registry.py          #   Auto-detection + parser dispatch
│   ├── markdown.py          #   .md with YAML front matter
│   ├── plaintext.py         #   .txt, stdin, Slack dumps
│   ├── yaml_input.py        #   .yaml/.yml/.json structured input
│   ├── pdf.py               #   .pdf via pdfplumber
│   ├── docx.py              #   .docx via python-docx
│   ├── jira.py              #   Jira JSON exports (API + list format)
│   ├── confluence.py        #   Confluence HTML via BS4 + markdownify
│   └── image.py             #   Image analysis via LLM vision
├── analyze/                # Phase 2 — LLM orchestration (async)
│   ├── analyzer.py          #   Orchestrator: extraction → dedup → risk → design
│   ├── prompts.py           #   3 system prompts (extraction, risk, design)
│   ├── models.py            #   10 dataclasses for analysis pipeline
│   ├── extraction.py        #   LLM JSON → typed AnalysisResult
│   ├── dedup.py             #   Jaccard word similarity deduplication
│   ├── conflicts.py         #   Conflict validation
│   ├── questions.py         #   Open question validation
│   ├── risks.py             #   Risk assessment parsing
│   └── design.py            #   Design output parsing (tasks, checks)
├── generate/               # Phase 3 — Jinja2 template rendering
│   ├── spec_builder.py      #   Orchestrates 6 spec files + lock
│   └── lock.py              #   spec.lock.yaml for reproducibility
├── verify/                 # Phase 4 — Acceptance check engine
│   ├── engine.py           #   4 check types: command, files_exist, pattern_*
│   └── reporter.py         #   Terminal (Rich), JSON, JUnit XML reporters
├── export/                 # Phase 5 — Agent-ready output
│   ├── base.py             #   Exporter Protocol
│   ├── registry.py         #   Format-based exporter dispatch
│   ├── architect.py        #   pipeline.yaml generation
│   └── generic.py          #   SPEC.md + verify.sh generation
├── diff/                   # Spec comparison
│   └── differ.py           #   Compare two specs by requirement/task IDs
├── doctor/                 # Environment health checks
│   └── checks.py            #   Python, API keys, deps, config validation
├── llm/                    # LiteLLM wrapper (used by analyze/ only)
│   └── adapter.py           #   Async completion, retry, cost tracking, budget
├── templates/              # Jinja2 templates for spec generation
│   ├── requirements.md.j2   #   FR, NFR, conflicts, open questions
│   ├── design.md.j2         #   Components, files, tech decisions
│   ├── tasks.md.j2          #   Task summary + detailed sections
│   ├── acceptance.yaml.j2   #   Executable acceptance checks
│   ├── context.md.j2        #   Project context for agents
│   └── sources.md.j2        #   Source traceability mapping
└── utils/                  # Shared utilities (logging, cost, detection)
    ├── file_detect.py       #   Extension-based format detection
    ├── project_detect.py    #   Auto-detect tech stack from project files
    ├── cost.py              #   Cost accumulation with per-phase breakdown
    └── logging.py           #   structlog configuration
```

**Key design principles:**

- **Protocol over ABC** — All extension points use `typing.Protocol`
- **Dataclasses for pipeline data, Pydantic for config** — Never mixed
- **Async only in analyze/** — Everything else is synchronous
- **Offline mode** — Parsing, verification, export, diff, doctor all work without LLM
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
# Generates CLAUDE.md + tasks + verify.sh
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

# Type check (strict)
mypy src/ --strict
```

Current test suite: **313 tests**, **83% coverage**.

### Implementation Status

| Phase | Module | Status |
|-------|--------|--------|
| Phase 1 — Ingest | `ingest/` (8 parsers + registry) | Implemented |
| Phase 2 — Analyze | `analyze/` (orchestrator + 7 sub-modules) | Implemented |
| Phase 3 — Generate | `generate/` (spec builder + 6 templates + lock) | Implemented |
| Phase 4 — Verify | `verify/` (engine + 3 reporters) | Implemented |
| Phase 5 — Export | `export/` (architect + generic) | Implemented |
| Standalone | `doctor/`, `config/`, `llm/`, `utils/` | Implemented |
| Standalone | `diff/` (spec differ) | Implemented |
| CLI | All 8 commands wired end-to-end | Implemented |

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
