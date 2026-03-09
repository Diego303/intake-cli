# intake — Seguimiento de Implementación v1.x

> Tracking de desarrollo a partir de v1.0.0.
> Para el historial detallado v0.1.0 → v1.0.0, ver [SEGUIMIENTO-V0.md](SEGUIMIENTO-V0.md).
> Actualizado: 2026-03-09

---

## Resumen v1.0.0

### Lo que es intake

CLI open-source que transforma requisitos de cualquier formato en specs verificables para agentes de IA.

```
INGEST (12 parsers) → ANALYZE (LLM) → GENERATE (6 spec files) → VERIFY (acceptance checks) → EXPORT (6 formatos de agente)
```

### Estadísticas del Release

| Métrica | Valor |
|---------|-------|
| **Tests** | 902 passed, 10 skipped, 0 failed |
| **mypy --strict** | 0 errors (91 source files) |
| **ruff** | 0 lint errors, 0 format issues (174 files) |
| **Source files** | 91 (.py) + 17 (.j2 templates) |
| **Test files** | 83 |
| **CLI commands** | 22 (14 top-level + 5 subcommands + 3 groups) |

### Pipeline (5 fases)

| Fase | Módulo | Qué hace |
|------|--------|----------|
| **1. Ingest** | `ingest/` | 12 parsers + registry con auto-detección de formato |
| **2. Analyze** | `analyze/` | Orquestador async con LLM: extracción, dedup, riesgos, diseño |
| **3. Generate** | `generate/` | Spec builder + adaptive builder + 6 spec files + lock |
| **4. Verify** | `verify/` | 4 tipos de check: command, files_exist, pattern_present, pattern_absent |
| **5. Export** | `export/` | 6 formatos: architect, claude-code, cursor, kiro, copilot, generic |

### 12 Parsers

| Parser | Formatos | Notas |
|--------|----------|-------|
| Markdown | `.md` | Front matter YAML, secciones por headings |
| Plaintext | `.txt`, stdin | Párrafos, Slack dumps |
| YAML/JSON | `.yaml`, `.yml`, `.json` | Requisitos estructurados |
| PDF | `.pdf` | pdfplumber (texto + tablas) |
| DOCX | `.docx` | python-docx (texto, tablas, metadata) |
| Jira | `.json` (auto-detected) | API + list format, comments, links |
| Confluence | `.html` (auto-detected) | BS4 + markdownify |
| Image | `.png`, `.jpg`, `.webp`, `.gif` | LLM vision |
| URL | `http://`, `https://` | httpx + markdownify |
| Slack | `.json` (auto-detected) | Messages, threads, decisions |
| GitHub Issues | `.json` (auto-detected) | Issues, labels, comments |
| GitLab Issues | `.json` (auto-detected) | Issues, notes, MRs, milestones |

### 4 Conectores API

| Conector | URI scheme | Librería |
|----------|-----------|----------|
| Jira | `jira://PROJ-123` | atlassian-python-api |
| Confluence | `confluence://SPACE/Title` | atlassian-python-api |
| GitHub | `github://org/repo/issues/42` | PyGithub |
| GitLab | `gitlab://group/project/issues/42` | python-gitlab v8.x |

### 6 Exporters

| Exporter | Output | Agente |
|----------|--------|--------|
| architect | `pipeline.yaml` | Claude architect |
| claude-code | `CLAUDE.md` + `.intake/tasks/` + `verify.sh` | Claude Code |
| cursor | `.cursor/rules/intake-spec.mdc` | Cursor |
| kiro | `requirements.md`, `design.md`, `tasks.md` | Kiro |
| copilot | `.github/copilot-instructions.md` | GitHub Copilot |
| generic | `SPEC.md` + `verify.sh` | Cualquier agente |

### 6 Spec Files

| Archivo | Propósito |
|---------|-----------|
| `requirements.md` | Requisitos funcionales y no funcionales (EARS) |
| `design.md` | Arquitectura, interfaces, decisiones técnicas |
| `tasks.md` | Tareas atómicas con dependencias y estado |
| `acceptance.yaml` | Checks ejecutables (generado con `yaml.dump`) |
| `context.md` | Contexto del proyecto para el agente |
| `sources.md` | Trazabilidad completa requisito → fuente |

### Módulos Standalone

| Módulo | Propósito |
|--------|-----------|
| `validate/` | Quality gate offline: 5 categorías de checks, DFS cycle detection |
| `estimate/` | Estimación de costes LLM: 7 modelos, 3 modos, budget warnings |
| `diff/` | Comparación de specs por IDs de requisitos y tareas |
| `doctor/` | Health checks: Python, API keys, deps, connectors, schema validation |
| `feedback/` | Análisis de fallos de verificación + sugerencias + enmiendas al spec |
| `mcp/` | Servidor MCP: 9 tools, resources, prompts (stdio + SSE) |
| `watch/` | File monitoring con watchfiles + auto-verificación |
| `templates/` | ChoiceLoader Jinja2: user templates → built-in |

### CLI Commands (22)

| Comando | Descripción |
|---------|-------------|
| `intake init` | Genera spec desde fuentes |
| `intake add` | Añade fuentes incrementalmente |
| `intake regenerate` | Regenera spec completo |
| `intake verify` | Verifica implementación (terminal/json/junit) |
| `intake export` | Exporta a formato de agente |
| `intake show` | Resumen del spec |
| `intake list` | Lista specs (recursivo) |
| `intake diff` | Compara dos specs |
| `intake doctor` | Health checks (+ `--fix`) |
| `intake feedback` | Analiza fallos y sugiere fixes |
| `intake validate` | Quality gate offline |
| `intake estimate` | Estimación de costes LLM |
| `intake export-ci` | Genera config CI/CD (GitLab/GitHub) |
| `intake watch` | Monitor + auto-verify |
| `intake plugins list` | Lista plugins descubiertos |
| `intake plugins check` | Valida compatibilidad |
| `intake task list` | Lista tareas con estado |
| `intake task update` | Actualiza estado de tarea |
| `intake mcp serve` | Servidor MCP (stdio/SSE) |

### Config

```
Prioridad: CLI flags > .intake.yaml > preset > defaults
Presets: minimal | standard | enterprise
15 modelos Pydantic v2: IntakeConfig, LLMConfig, ProjectConfig, SpecConfig,
  VerificationConfig, ExportConfig, SecurityConfig, ConnectorsConfig (Jira,
  Confluence, GitHub, GitLab), FeedbackConfig, MCPConfig, WatchConfig,
  ValidateConfig, EstimateConfig, TemplatesConfig
```

### Stack Técnico

| Componente | Tecnología |
|------------|------------|
| CLI | Click |
| LLM | LiteLLM (provider-agnostic) |
| Config | Pydantic v2 |
| Templates | Jinja2 |
| Terminal | Rich |
| Logging | structlog (→ stderr) |
| PDF | pdfplumber |
| DOCX | python-docx |
| HTML | BeautifulSoup4 + markdownify |
| Tests | pytest + pytest-asyncio |
| Types | mypy --strict |
| Lint | ruff |
| Package | pyproject.toml + hatchling |

### Lecciones Clave (de QA v1.0.0)

1. **Nunca usar `model_copy(update=...)` para modelos Pydantic anidados** → usar `model_validate()` (BUG-006)
2. **Nunca usar Jinja2 para generar YAML con contenido dinámico** → usar `yaml.dump()` (BUG-008)
3. **Los LLMs inventan check types** → normalizar con alias map + fallback (BUG-009)
4. **structlog a stderr siempre** para outputs parseables en stdout (BUG-012)

---

## Historial de Versiones

| Versión | Fecha | Tests | Hitos |
|---------|-------|-------|-------|
| v0.1.0 | 2026-02 | 313 | 8 parsers, LLM analysis, generation, verification, 2 exporters, doctor, diff |
| v0.2.0 | 2026-03-03 | 673 | Plugin system, 3 connectors, 4 exporters, feedback loop |
| v0.3.0 | 2026-03-04 | 673 | Enterprise docs, SECURITY.md |
| v0.4.0 | 2026-03-05 | 772 | MCP server (9 tools), watch mode |
| v0.5.0 | 2026-03-07 | 775 | GitHub Action, CI pipeline, 5 examples, mypy strict |
| v0.6.0 | 2026-03-07 | 882 | GitLab connector+parser, validate, estimate, templates, CI export |
| **v1.0.0** | **2026-03-09** | **902** | **QA final: 12 bugs corregidos, release ready** |

---

## Desarrollo v1.x

> A partir de aquí se documenta el desarrollo post-v1.0.0.

<!-- Próximas entradas van aquí -->
