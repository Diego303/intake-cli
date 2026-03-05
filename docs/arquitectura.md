# Arquitectura

## Vision general

intake procesa requisitos a traves de un pipeline de 5 fases:

```
INGEST (parsers) -> ANALYZE (LLM) -> GENERATE (spec files) -> VERIFY (checks) -> EXPORT (output)
```

Cada fase es un modulo independiente con responsabilidades claras. Las dependencias fluyen en una sola direccion: de arriba hacia abajo.

---

## Flujo de dependencias entre modulos

```
cli.py                    <- Adaptador CLI delgado, sin logica de negocio
  |
config/                   <- Se carga primero, se inyecta en todos los modulos
  |
plugins/                  <- Descubrimiento de plugins via entry_points (PEP 621)
  |
ingest/                   <- FASE 1: 11 parsers + plugin discovery. Sin dependencia de LLM.
  |
analyze/                  <- FASE 2: Unico modulo que habla con el LLM + clasificacion de complejidad
  |
generate/                 <- FASE 3: Templates Jinja2 + generacion adaptativa. Sin dependencia de LLM.
  |
verify/                   <- FASE 4: Ejecucion de subprocesos. Sin dependencia de LLM.
  |
export/                   <- FASE 5: Generacion de archivos + plugin discovery. Sin dependencia de LLM.

connectors/               <- 3 conectores API: Jira, Confluence, GitHub (async fetch)
  |
feedback/                 <- Feedback loop: analisis de fallos + enmiendas a la spec (requiere LLM)

mcp/                      <- Servidor MCP: tools, resources, prompts (requiere LLM para feedback)
watch/                    <- Watch mode: monitoreo de archivos + re-verificacion (usa verify/)

diff/                     <- Standalone: compara directorios de specs
doctor/                   <- Standalone: checks del entorno + validacion de credenciales
llm/                      <- Compartido: usado por analyze/ y feedback/
utils/                    <- Compartido: usado por cualquier modulo
```

### Regla critica de aislamiento

Los modulos `ingest/`, `generate/`, `verify/`, `export/`, `diff/` y `doctor/` **nunca** importan de `llm/` ni de `analyze/`. Esto garantiza que todo excepto `init`, `add` y `feedback` funcione offline.

Excepciones documentadas:
- `ImageParser` acepta un callable de vision inyectado (no importa directamente del LLM)
- `feedback/` usa el LLM para analizar fallos de verificacion, pero no analiza requisitos — es un modulo independiente de `analyze/`

---

## Estructura de directorios

```
src/intake/
├── cli.py                  # Click CLI — adaptador delgado, sin logica
├── config/                 # Modelos Pydantic v2, presets, loader
│   ├── schema.py           #   11 modelos de config (LLM, Project, Spec, Verification, Export, Security, Connectors, Feedback, MCP, Watch, Intake)
│   ├── presets.py           #   minimal / standard / enterprise
│   ├── loader.py            #   Merge por capas: defaults -> preset -> YAML -> CLI
│   └── defaults.py          #   Constantes centralizadas
├── plugins/                # Sistema de plugins (v0.2.0)
│   ├── protocols.py         #   Protocolos V2: ParserPlugin, ExporterPlugin, ConnectorPlugin
│   ├── discovery.py         #   Descubrimiento via importlib.metadata.entry_points()
│   └── hooks.py             #   Sistema de hooks del pipeline (HookManager)
├── connectors/             # 3 conectores API directos (async fetch + plugin protocol)
│   ├── base.py              #   ConnectorRegistry, ConnectorError
│   ├── jira_api.py          #   Jira: issues, JQL, sprints via atlassian-python-api
│   ├── confluence_api.py    #   Confluence: paginas por ID, space/titulo, CQL
│   └── github_api.py        #   GitHub: issues individuales, filtrados, por labels
├── ingest/                 # Fase 1 — 11 parsers + registry + plugin discovery + auto-deteccion
│   ├── base.py              #   ParsedContent dataclass + Parser Protocol
│   ├── registry.py          #   Auto-deteccion + plugin discovery + dispatch de parsers
│   ├── markdown.py          #   .md con YAML front matter
│   ├── plaintext.py         #   .txt, stdin, dumps de Slack
│   ├── yaml_input.py        #   .yaml/.yml/.json estructurado
│   ├── pdf.py               #   .pdf via pdfplumber
│   ├── docx.py              #   .docx via python-docx
│   ├── jira.py              #   Exports JSON de Jira (formato API + lista)
│   ├── confluence.py        #   HTML de Confluence via BS4 + markdownify
│   ├── image.py             #   Analisis de imagenes via LLM vision
│   ├── url.py               #   HTTP/HTTPS URLs via httpx + markdownify
│   ├── slack.py             #   Exports JSON de Slack (mensajes, threads, decisiones)
│   └── github_issues.py     #   GitHub Issues JSON (issues, labels, comments)
├── analyze/                # Fase 2 — Orquestacion LLM (async) + clasificacion
│   ├── analyzer.py          #   Orquestador: extraction -> dedup -> risk -> design
│   ├── prompts.py           #   3 system prompts (extraction, risk, design)
│   ├── models.py            #   10 dataclasses del pipeline de analisis
│   ├── complexity.py        #   Clasificacion heuristica de complejidad (quick/standard/enterprise)
│   ├── extraction.py        #   JSON del LLM -> AnalysisResult tipado
│   ├── dedup.py             #   Deduplicacion por similaridad Jaccard
│   ├── conflicts.py         #   Validacion de conflictos
│   ├── questions.py         #   Validacion de preguntas abiertas
│   ├── risks.py             #   Parsing de evaluacion de riesgos
│   └── design.py            #   Parsing del diseno (tareas, checks)
├── generate/               # Fase 3 — Renderizado de templates Jinja2 + generacion adaptativa
│   ├── spec_builder.py      #   Orquesta 6 archivos spec + lock
│   ├── adaptive.py          #   AdaptiveSpecBuilder — seleccion de archivos segun modo
│   └── lock.py              #   spec.lock.yaml para reproducibilidad
├── verify/                 # Fase 4 — Motor de checks de aceptacion
│   ├── engine.py            #   4 tipos: command, files_exist, pattern_present, pattern_absent
│   └── reporter.py          #   Terminal (Rich), JSON, JUnit XML
├── export/                 # Fase 5 — Output listo para agentes + plugin discovery (6 exporters)
│   ├── base.py              #   Exporter Protocol
│   ├── registry.py          #   Plugin discovery + dispatch por formato
│   ├── _helpers.py          #   Utilidades compartidas (read_spec_file, parse_tasks, etc.)
│   ├── architect.py         #   Genera pipeline.yaml (V1)
│   ├── generic.py           #   Genera SPEC.md + verify.sh (V1)
│   ├── claude_code.py       #   CLAUDE.md + .intake/tasks/ + verify.sh (V2)
│   ├── cursor.py            #   .cursor/rules/intake-spec.mdc (V2)
│   ├── kiro.py              #   requirements/design/tasks en formato Kiro (V2)
│   └── copilot.py           #   .github/copilot-instructions.md (V2)
├── diff/                   # Comparacion de specs
│   └── differ.py            #   Compara por IDs de requisitos/tareas
├── doctor/                 # Checks de salud del entorno
│   └── checks.py            #   Python, API keys, deps, config + auto-fix
├── llm/                    # Wrapper LiteLLM (solo usado por analyze/)
│   └── adapter.py           #   Completion async, retry, cost tracking, budget
├── feedback/               # Feedback loop: analisis de fallos + enmiendas (requiere LLM)
│   ├── analyzer.py          #   FeedbackAnalyzer: analisis LLM de checks fallidos
│   ├── prompts.py           #   FEEDBACK_ANALYSIS_PROMPT
│   ├── suggestions.py       #   SuggestionFormatter: generic, claude-code, cursor
│   └── spec_updater.py      #   SpecUpdater: preview + apply de enmiendas a la spec
├── mcp/                    # Servidor MCP (Model Context Protocol)
│   ├── __init__.py         #   MCPError + re-exports (create_server, run_stdio, run_sse)
│   ├── server.py           #   Creacion del servidor + transportes stdio/SSE
│   ├── tools.py            #   7 tools: show, context, tasks, update, verify, feedback, list
│   ├── resources.py        #   Recursos dinamicos: intake://specs/{name}/{section}
│   └── prompts.py          #   Templates: implement_next_task, verify_and_fix
├── watch/                  # Watch mode (monitoreo + re-verificacion)
│   ├── __init__.py         #   WatchError exception
│   └── watcher.py          #   SpecWatcher con watchfiles (Rust-based)
├── templates/              # 15 templates Jinja2 (6 spec + 3 claude-code + 3 kiro + 1 cursor + 1 copilot + 1 feedback)
│   ├── requirements.md.j2
│   ├── design.md.j2
│   ├── tasks.md.j2          #   Incluye columna de Status por tarea
│   ├── acceptance.yaml.j2
│   ├── context.md.j2
│   ├── sources.md.j2
│   ├── claude_md.j2         #   Seccion para CLAUDE.md
│   ├── claude_task.md.j2    #   Tarea individual para Claude Code
│   ├── verify_sh.j2         #   Script de verificacion
│   ├── cursor_rules.mdc.j2  #   Reglas de Cursor
│   ├── kiro_requirements.md.j2  #   Requisitos en formato Kiro
│   ├── kiro_design.md.j2    #   Diseno en formato Kiro
│   ├── kiro_tasks.md.j2     #   Tareas en formato Kiro
│   ├── copilot_instructions.md.j2  #   Instrucciones para Copilot
│   └── feedback.md.j2       #   Formato de sugerencias de feedback
└── utils/                  # Utilidades compartidas
    ├── file_detect.py       #   Deteccion de formato por extension
    ├── project_detect.py    #   Auto-deteccion del stack tecnologico
    ├── source_uri.py        #   Parsing de URIs: file, stdin, url, jira://, github://
    ├── task_state.py        #   Gestion de estado de tareas en tasks.md
    ├── cost.py              #   Tracking de costos con desglose por fase
    └── logging.py           #   Configuracion de structlog
```

---

## Modelos de datos

intake usa dos sistemas de modelado con propositos distintos:

### Dataclasses — Datos del pipeline

Todos los datos que fluyen por el pipeline usan `dataclasses` de la biblioteca estandar. Son ligeros y no necesitan validacion porque los datos ya vienen procesados internamente.

Ejemplos: `ParsedContent`, `Requirement`, `Conflict`, `TaskItem`, `CheckResult`, `AnalysisResult`, `DesignResult`.

### Pydantic v2 — Configuracion

Todo lo que viene del exterior (archivo `.intake.yaml`, flags CLI) se valida con modelos Pydantic v2. Esto garantiza que la configuracion es correcta antes de usarla.

Ejemplos: `IntakeConfig`, `LLMConfig`, `ProjectConfig`, `SpecConfig`.

**Regla:** Nunca se mezclan. Los modelos de config no aparecen dentro de los datos del pipeline, y los dataclasses no validan input del usuario.

---

## Puntos de extension: Protocol over ABC

Todos los puntos de extension usan `typing.Protocol` con `@runtime_checkable`, no clases abstractas (ABC). Esto permite subtipado estructural sin herencia:

```python
@runtime_checkable
class Parser(Protocol):
    def can_parse(self, source: str) -> bool: ...
    def parse(self, source: str) -> ParsedContent: ...
```

### Protocolos V1 (core)

Los Protocols V1 del sistema son:

| Protocol | Modulo | Metodos |
|----------|--------|---------|
| `Parser` | `ingest/base.py` | `can_parse(source) -> bool`, `parse(source) -> ParsedContent` |
| `Exporter` | `export/base.py` | `export(spec_dir, output_dir) -> list[str]` |
| `Reporter` | `verify/reporter.py` | `render(report) -> str` |

### Protocolos V2 (plugins)

Los Protocols V2 extienden los V1 con metadata y capacidades adicionales para plugins externos:

| Protocol | Modulo | Metodos |
|----------|--------|---------|
| `ParserPlugin` | `plugins/protocols.py` | `meta`, `supported_extensions`, `confidence()`, `can_parse()`, `parse()` |
| `ExporterPlugin` | `plugins/protocols.py` | `meta`, `supported_agents`, `export() -> ExportResult` |
| `ConnectorPlugin` | `plugins/protocols.py` | `meta`, `uri_schemes`, `can_handle()`, `fetch()` (async), `validate_config()` |

Los parsers existentes (V1) siguen funcionando. Los registries aceptan tanto V1 como V2. Para agregar un nuevo parser, exporter o reporter, solo hay que implementar la interfaz correcta — no es necesario heredar de ninguna clase base.

Ver [Plugins](plugins.md) para mas detalles.

---

## Los 7 archivos spec

Cada spec generada contiene estos archivos:

| Archivo | Generado por | Contenido |
|---------|-------------|-----------|
| `requirements.md` | `requirements.md.j2` | Requisitos funcionales (FR-XX) y no funcionales (NFR-XX), conflictos, preguntas abiertas |
| `design.md` | `design.md.j2` | Componentes, archivos a crear/modificar, decisiones tecnicas, dependencias |
| `tasks.md` | `tasks.md.j2` | Tabla resumen + detalle por tarea: descripcion, archivos, dependencias, checks |
| `acceptance.yaml` | `acceptance.yaml.j2` | Checks ejecutables: command, files_exist, pattern_present, pattern_absent |
| `context.md` | `context.md.j2` | Info del proyecto, stack, convenciones, resumen de riesgos |
| `sources.md` | `sources.md.j2` | Fuentes usadas, mapeo requisito-fuente, fuentes de conflictos |
| `spec.lock.yaml` | `lock.py` | Hashes SHA-256 de fuentes y specs, costo total, timestamps |

---

## Jerarquia de excepciones

Cada modulo define sus propias excepciones con mensajes orientados al usuario. Todas incluyen `reason` (que paso) y `suggestion` (como solucionarlo).

```
IngestError
├── ParseError(source, reason, suggestion)
│   ├── EmptySourceError(source)
│   └── FileTooLargeError(source, size_bytes)
└── UnsupportedFormatError(source, detected_format)

AnalyzeError(reason, suggestion)

GenerateError(reason, suggestion)

VerifyError(reason, suggestion)

ExportError(reason, suggestion)

DiffError(reason, suggestion)

DoctorError

ConfigError(reason, suggestion)

PresetError(preset_name)

LLMError(reason, suggestion)
├── CostLimitError(accumulated, limit)
└── APIKeyMissingError(env_var)

PluginError
└── PluginLoadError

ConnectorError
└── ConnectorNotFoundError

FeedbackError

SpecUpdateError

MCPError

WatchError

TaskStateError
```

---

## Dependencias externas

| Paquete | Version | Uso |
|---------|---------|-----|
| `click` | >=8.1 | Framework CLI |
| `rich` | >=13.0 | Output en terminal (tablas, colores) |
| `pydantic` | >=2.0 | Validacion de configuracion |
| `pyyaml` | >=6.0 | Parsing YAML |
| `litellm` | >=1.40 | Abstraccion LLM (100+ modelos) |
| `pdfplumber` | >=0.11 | Parsing de PDFs |
| `python-docx` | >=1.1 | Parsing de DOCX |
| `beautifulsoup4` | >=4.12 | Parsing HTML |
| `markdownify` | >=0.13 | Conversion HTML a Markdown |
| `jinja2` | >=3.1 | Renderizado de templates |
| `structlog` | >=24.0 | Logging estructurado |
| `httpx` | >=0.27 | HTTP client (URL parser, conectores) |

**Dependencias opcionales (conectores):**

| Paquete | Version | Uso |
|---------|---------|-----|
| `atlassian-python-api` | >=3.40 | Conectores Jira y Confluence |
| `PyGithub` | >=2.0 | Conector GitHub |
| `mcp` | >=1.0 | Servidor MCP (tools, resources, prompts) |
| `watchfiles` | >=1.0 | Watch mode (monitoreo de archivos, Rust-based) |

---

## Sistema de plugins

Desde v0.2.0, intake usa una arquitectura plugin-first basada en entry_points de Python (PEP 621).

### Descubrimiento

Los plugins se descubren automaticamente via `importlib.metadata.entry_points()` en tres grupos:

| Grupo | Contenido |
|-------|-----------|
| `intake.parsers` | 11 parsers built-in |
| `intake.exporters` | 6 exporters built-in (2 V1 + 4 V2) |
| `intake.connectors` | 3 connectors built-in (Jira, Confluence, GitHub) |

Los registries (`ParserRegistry`, `ExporterRegistry`) intentan plugin discovery primero y caen back a registro manual si falla. Esto permite que plugins externos se registren automaticamente con solo instalar el paquete.

### Hooks

El `HookManager` permite registrar callbacks que se ejecutan en respuesta a eventos del pipeline. Los callbacks se ejecutan en orden de registro; las excepciones se capturan sin bloquear otros callbacks.

Ver [Plugins](plugins.md) para documentacion completa.

---

## Clasificacion de complejidad y generacion adaptativa

El modulo `analyze/complexity.py` clasifica automaticamente la complejidad de las fuentes para seleccionar el modo de generacion optimo:

| Modo | Criterios | Archivos generados |
|------|-----------|-------------------|
| `quick` | <500 palabras, 1 fuente, sin estructura | `context.md` + `tasks.md` |
| `standard` | Default | Los 6 archivos spec completos |
| `enterprise` | 4+ fuentes O >5000 palabras | Los 6 archivos + riesgos detallados |

El `AdaptiveSpecBuilder` envuelve al `SpecBuilder` estandar y filtra los archivos segun el modo. Se puede forzar un modo especifico con `--mode` en el CLI.

---

## Principios de diseno

1. **Offline primero** — Todo excepto `init` y `add` funciona sin conexion a internet.
2. **Provider-agnostic** — Cualquier modelo que LiteLLM soporte: Anthropic, OpenAI, Google, modelos locales.
3. **Plugin-first** — Parsers y exporters se descubren via entry_points. Fallback a registro manual.
4. **Sin magic strings** — Todas las constantes estan definidas explicitamente en `defaults.py`.
5. **Budget enforcement** — El costo se trackea por llamada LLM con limites configurables.
6. **Tipado estricto** — `mypy --strict` con cero errores en todo el codebase.
7. **Errores informativos** — Cada excepcion dice que paso, por que, y como solucionarlo.
