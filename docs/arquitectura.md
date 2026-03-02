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
ingest/                   <- FASE 1: Parsers. Sin dependencia de LLM.
  |
analyze/                  <- FASE 2: Unico modulo que habla con el LLM.
  |
generate/                 <- FASE 3: Templates Jinja2. Sin dependencia de LLM.
  |
verify/                   <- FASE 4: Ejecucion de subprocesos. Sin dependencia de LLM.
  |
export/                   <- FASE 5: Generacion de archivos. Sin dependencia de LLM.

diff/                     <- Standalone: compara directorios de specs
doctor/                   <- Standalone: checks del entorno
llm/                      <- Compartido: SOLO usado por analyze/
utils/                    <- Compartido: usado por cualquier modulo
```

### Regla critica de aislamiento

Los modulos `ingest/`, `generate/`, `verify/`, `export/`, `diff/` y `doctor/` **nunca** importan de `llm/` ni de `analyze/`. Solo `analyze/` se comunica con el LLM. Esto garantiza que todo excepto `init` y `add` funcione offline.

La unica excepcion es `ImageParser`, que acepta un callable de vision inyectado (no importa directamente del LLM).

---

## Estructura de directorios

```
src/intake/
├── cli.py                  # Click CLI — adaptador delgado, sin logica
├── config/                 # Modelos Pydantic v2, presets, loader
│   ├── schema.py           #   6 modelos de config (LLM, Project, Spec, Verification, Export, Security)
│   ├── presets.py           #   minimal / standard / enterprise
│   ├── loader.py            #   Merge por capas: defaults -> preset -> YAML -> CLI
│   └── defaults.py          #   Constantes centralizadas
├── ingest/                 # Fase 1 — 8 parsers + registry + auto-deteccion
│   ├── base.py              #   ParsedContent dataclass + Parser Protocol
│   ├── registry.py          #   Auto-deteccion + dispatch de parsers
│   ├── markdown.py          #   .md con YAML front matter
│   ├── plaintext.py         #   .txt, stdin, dumps de Slack
│   ├── yaml_input.py        #   .yaml/.yml/.json estructurado
│   ├── pdf.py               #   .pdf via pdfplumber
│   ├── docx.py              #   .docx via python-docx
│   ├── jira.py              #   Exports JSON de Jira (formato API + lista)
│   ├── confluence.py        #   HTML de Confluence via BS4 + markdownify
│   └── image.py             #   Analisis de imagenes via LLM vision
├── analyze/                # Fase 2 — Orquestacion LLM (async)
│   ├── analyzer.py          #   Orquestador: extraction -> dedup -> risk -> design
│   ├── prompts.py           #   3 system prompts (extraction, risk, design)
│   ├── models.py            #   10 dataclasses del pipeline de analisis
│   ├── extraction.py        #   JSON del LLM -> AnalysisResult tipado
│   ├── dedup.py             #   Deduplicacion por similaridad Jaccard
│   ├── conflicts.py         #   Validacion de conflictos
│   ├── questions.py         #   Validacion de preguntas abiertas
│   ├── risks.py             #   Parsing de evaluacion de riesgos
│   └── design.py            #   Parsing del diseno (tareas, checks)
├── generate/               # Fase 3 — Renderizado de templates Jinja2
│   ├── spec_builder.py      #   Orquesta 6 archivos spec + lock
│   └── lock.py              #   spec.lock.yaml para reproducibilidad
├── verify/                 # Fase 4 — Motor de checks de aceptacion
│   ├── engine.py            #   4 tipos: command, files_exist, pattern_present, pattern_absent
│   └── reporter.py          #   Terminal (Rich), JSON, JUnit XML
├── export/                 # Fase 5 — Output listo para agentes
│   ├── base.py              #   Exporter Protocol
│   ├── registry.py          #   Dispatch por formato
│   ├── architect.py         #   Genera pipeline.yaml
│   └── generic.py           #   Genera SPEC.md + verify.sh
├── diff/                   # Comparacion de specs
│   └── differ.py            #   Compara por IDs de requisitos/tareas
├── doctor/                 # Checks de salud del entorno
│   └── checks.py            #   Python, API keys, deps, config + auto-fix
├── llm/                    # Wrapper LiteLLM (solo usado por analyze/)
│   └── adapter.py           #   Completion async, retry, cost tracking, budget
├── templates/              # Templates Jinja2 para generacion de specs
│   ├── requirements.md.j2
│   ├── design.md.j2
│   ├── tasks.md.j2
│   ├── acceptance.yaml.j2
│   ├── context.md.j2
│   └── sources.md.j2
└── utils/                  # Utilidades compartidas
    ├── file_detect.py       #   Deteccion de formato por extension
    ├── project_detect.py    #   Auto-deteccion del stack tecnologico
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

Los tres Protocols del sistema son:

| Protocol | Modulo | Metodos |
|----------|--------|---------|
| `Parser` | `ingest/base.py` | `can_parse(source) -> bool`, `parse(source) -> ParsedContent` |
| `Exporter` | `export/base.py` | `export(spec_dir, output_dir) -> list[str]` |
| `Reporter` | `verify/reporter.py` | `render(report) -> str` |

Para agregar un nuevo parser, exporter o reporter, solo hay que implementar la interfaz correcta — no es necesario heredar de ninguna clase base.

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
| `httpx` | >=0.27 | HTTP client (integraciones futuras) |

---

## Principios de diseno

1. **Offline primero** — Todo excepto `init` y `add` funciona sin conexion a internet.
2. **Provider-agnostic** — Cualquier modelo que LiteLLM soporte: Anthropic, OpenAI, Google, modelos locales.
3. **Sin magic strings** — Todas las constantes estan definidas explicitamente en `defaults.py`.
4. **Budget enforcement** — El costo se trackea por llamada LLM con limites configurables.
5. **Tipado estricto** — `mypy --strict` con cero errores en todo el codebase.
6. **Errores informativos** — Cada excepcion dice que paso, por que, y como solucionarlo.
