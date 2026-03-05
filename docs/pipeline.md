# Pipeline

intake procesa requisitos a traves de un pipeline de 5 fases. Cada fase transforma los datos y los pasa a la siguiente.

```
Fuentes             Fase 1        Fase 2        Fase 3         Fase 4          Fase 5
(archivos/URLs) --> INGEST -----> ANALYZE ----> GENERATE ----> VERIFY -------> EXPORT
                    (parsers)     (LLM)        (templates)    (checks)        (output)
                       |             |              |              |               |
                 ParsedContent  AnalysisResult  Spec files   VerifyReport   Agent output
                                     |              |
                              Complexity      Adaptive
                             Assessment      Generation
```

---

## Fase 1: Ingest

**Modulo:** `ingest/` (11 parsers)
**Requiere LLM:** No (excepto `ImageParser`)

### Que hace

Toma archivos de requisitos en cualquier formato y los convierte en una estructura normalizada (`ParsedContent`). Soporta archivos locales, URLs, y stdin.

### Flujo

```
Fuente --> parse_source() --> Registry --> Detecta formato --> Selecciona parser --> ParsedContent
```

1. **Resolucion de fuente**: `parse_source()` determina el tipo de fuente:
   - Archivos locales → pasan al registry
   - URLs HTTP/HTTPS → se procesan con `UrlParser`
   - URIs de esquema (`jira://`, `confluence://`, `github://`) → se resuelven via conectores API (descargan a archivos temporales)
   - Stdin (`-`) → se lee como plaintext
   - Texto libre → se trata como plaintext
2. El **Registry** recibe la ruta del archivo
3. **Auto-detecta el formato** por extension y contenido:
   - Extension directa: `.md` -> markdown, `.pdf` -> pdf, `.docx` -> docx
   - Subtipos JSON: Jira > GitHub Issues > Slack > YAML generico
   - Subtipos HTML: si contiene "confluence" o "atlassian" -> confluence
   - Fallback: plaintext
4. **Selecciona el parser** registrado para ese formato (via plugin discovery o registro manual)
5. El parser produce un **`ParsedContent`** normalizado

### ParsedContent

Cada fuente parseada produce:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `text` | string | Texto limpio extraido |
| `format` | string | Identificador del formato (ej: `"jira"`, `"markdown"`) |
| `source` | string | Path al archivo original |
| `metadata` | dict | Pares clave-valor (autor, fecha, prioridad, etc.) |
| `sections` | list[dict] | Secciones estructuradas (titulo, nivel, contenido) |
| `relations` | list[dict] | Relaciones entre items (blocks, depends on, relates to) |

### Validaciones

Antes de parsear, cada archivo pasa por validaciones centralizadas:

- El archivo debe existir y ser un archivo regular (no directorio)
- Tamano maximo: **50 MB** (`MAX_FILE_SIZE_BYTES`)
- Si el archivo esta vacio o solo tiene whitespace: error `EmptySourceError`
- Encoding: intenta UTF-8 primero, fallback a latin-1

Ver [Formatos de entrada](formatos-entrada.md) para detalles de cada parser.

---

## Fase 2: Analyze

**Modulo:** `analyze/`
**Requiere LLM:** Si (async via `litellm.acompletion`)

### Que hace

Toma los `ParsedContent` de todas las fuentes y usa el LLM para extraer requisitos estructurados, detectar conflictos, evaluar riesgos y producir un diseno tecnico.

### Sub-fases

```
ParsedContent[] --> Combine --> Extraction --> Dedup --> Validate --> Risk --> Design --> AnalysisResult
```

#### 1. Combinar fuentes

Concatena el texto de todas las fuentes con separadores:

```
=== SOURCE 1: path/to/file.md (format: markdown) ===
[contenido]

---

=== SOURCE 2: path/to/jira.json (format: jira) ===
[contenido]
```

#### 2. Extraccion (llamada LLM)

Envia el texto combinado al LLM con `EXTRACTION_PROMPT`. El LLM retorna JSON con:

- **Requisitos funcionales** (FR-01, FR-02, ...)
- **Requisitos no funcionales** (NFR-01, NFR-02, ...)
- **Conflictos** entre fuentes (CONFLICT-01, ...)
- **Preguntas abiertas** (Q-01, Q-02, ...)

El prompt se configura con: numero de fuentes, idioma, formato de requisitos (`ears`, `user-stories`, etc.).

#### 3. Deduplicacion

Compara titulos de requisitos usando **similaridad Jaccard** (interseccion de palabras / union de palabras):

- Threshold: **0.75** (75% de palabras en comun = duplicado)
- Normaliza: lowercase, strip, colapsa whitespace
- Deduplica funcionales y no funcionales por separado
- Conserva la primera ocurrencia

#### 4. Validacion

- **Conflictos**: se filtran los que no tienen descripcion, fuentes, o recomendacion
- **Preguntas abiertas**: se filtran las que no tienen texto de pregunta o contexto

#### 5. Evaluacion de riesgos (opcional)

Si `config.spec.risk_assessment = true`, hace otra llamada LLM con `RISK_ASSESSMENT_PROMPT`. Produce una lista de riesgos (RISK-01, ...) con:

- IDs de requisitos asociados
- Probabilidad e impacto (low/medium/high)
- Categoria (technical, scope, integration, security, performance)
- Mitigacion sugerida

#### 6. Diseno (llamada LLM)

Tercera llamada LLM con `DESIGN_PROMPT`. Produce:

- **Componentes** de arquitectura
- **Archivos a crear y modificar** (path + descripcion + accion)
- **Decisiones tecnicas** (decision, justificacion, requisito asociado)
- **Tareas** con dependencias (DAG), estimacion en minutos, archivos, checks
- **Checks de aceptacion** (command, files_exist, pattern_present, pattern_absent)
- **Dependencias** externas del proyecto

### AnalysisResult

El resultado completo contiene:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `functional_requirements` | list[Requirement] | Requisitos funcionales (FR-XX) |
| `non_functional_requirements` | list[Requirement] | Requisitos no funcionales (NFR-XX) |
| `conflicts` | list[Conflict] | Conflictos entre fuentes |
| `open_questions` | list[OpenQuestion] | Preguntas sin responder |
| `risks` | list[RiskItem] | Evaluacion de riesgos |
| `design` | DesignResult | Diseno tecnico con tareas y checks |
| `duplicates_removed` | int | Cantidad de duplicados eliminados |
| `total_cost` | float | Costo total del analisis en USD |
| `model_used` | string | Modelo LLM utilizado |

### Control de costos

El `LLMAdapter` rastrea el costo de cada llamada:

- Acumula `total_cost`, `total_input_tokens`, `total_output_tokens`
- Despues de cada llamada, compara con `max_cost_per_spec`
- Si se excede el presupuesto, lanza `CostLimitError` y el analisis se detiene
- El costo se calcula via `litellm.completion_cost()`

---

## Fase 2.5: Clasificacion de complejidad

**Modulo:** `analyze/complexity.py`
**Requiere LLM:** No

### Que hace

Antes de generar, se clasifica la complejidad de las fuentes para seleccionar el modo de generacion optimo. Esta clasificacion es heuristica (no usa LLM).

### Criterios

| Modo | Condiciones | Confianza |
|------|------------|-----------|
| `quick` | <500 palabras AND 1 fuente AND sin contenido estructurado | Alta |
| `enterprise` | 4+ fuentes O >5000 palabras | Alta |
| `standard` | Todo lo que no es quick ni enterprise | Media |

**Contenido estructurado** incluye formatos como `jira`, `confluence`, `yaml`, `github_issues`, `slack`.

La clasificacion se puede sobreescribir con `--mode` en la CLI.

---

## Fase 3: Generate

**Modulo:** `generate/`
**Requiere LLM:** No

### Que hace

Toma el `AnalysisResult` y renderiza archivos Markdown/YAML usando templates Jinja2, mas un `spec.lock.yaml` para reproducibilidad. La cantidad de archivos generados depende del modo.

### Generacion adaptativa

El `AdaptiveSpecBuilder` envuelve al `SpecBuilder` estandar y filtra los archivos segun el modo:

| Modo | Archivos generados |
|------|-------------------|
| `quick` | `context.md`, `tasks.md` |
| `standard` | Los 6 archivos completos |
| `enterprise` | Los 6 archivos + riesgos detallados |

### Templates

| Archivo generado | Template | Contenido principal |
|-----------------|----------|---------------------|
| `requirements.md` | `requirements.md.j2` | FR, NFR, conflictos, preguntas abiertas |
| `design.md` | `design.md.j2` | Componentes, archivos, decisiones, dependencias |
| `tasks.md` | `tasks.md.j2` | Tabla resumen + detalle por tarea |
| `acceptance.yaml` | `acceptance.yaml.j2` | Checks ejecutables por tipo |
| `context.md` | `context.md.j2` | Info del proyecto, stack, riesgos |
| `sources.md` | `sources.md.j2` | Fuentes, trazabilidad, conflictos |

### spec.lock.yaml

Archivo de reproducibilidad con:

| Campo | Descripcion |
|-------|-------------|
| `version` | Version del formato del lock (actualmente "1") |
| `created_at` | Timestamp ISO de creacion |
| `model` | Modelo LLM utilizado |
| `config_hash` | Hash de la configuracion usada |
| `source_hashes` | Mapa de archivo -> SHA-256 (primeros 16 hex chars) |
| `spec_hashes` | Mapa de archivo spec -> SHA-256 |
| `total_cost` | Costo total del analisis en USD |
| `requirement_count` | Cantidad de requisitos |
| `task_count` | Cantidad de tareas |

Se usa para detectar si las fuentes cambiaron desde la ultima generacion (`is_stale()`).

---

## Fase 4: Verify

**Modulo:** `verify/`
**Requiere LLM:** No

### Que hace

Ejecuta los checks definidos en `acceptance.yaml` contra el directorio del proyecto. Produce un reporte con resultados.

### Tipos de checks

| Tipo | Que verifica | Campos usados |
|------|-------------|---------------|
| `command` | Ejecuta un comando shell y verifica exit code == 0 | `command` |
| `files_exist` | Verifica que todos los paths listados existen | `paths` |
| `pattern_present` | Verifica que patrones regex existen en archivos que matchean el glob | `glob`, `patterns` |
| `pattern_absent` | Verifica que patrones regex NO existen en archivos que matchean el glob | `glob`, `patterns` |

### Formatos de reporte

| Formato | Clase | Uso |
|---------|-------|-----|
| `terminal` | `TerminalReporter` | Tabla Rich con colores en la terminal |
| `json` | `JsonReporter` | JSON machine-readable |
| `junit` | `JunitReporter` | XML JUnit para CI (GitHub Actions, Jenkins) |

Ver [Verificacion](verificacion.md) para detalles completos.

---

## Fase 5: Export

**Modulo:** `export/`
**Requiere LLM:** No

### Que hace

Toma los archivos spec generados y los transforma en un formato listo para un agente IA especifico.

### Formatos disponibles

| Formato | Que genera | Mejor para |
|---------|-----------|-----------|
| `architect` | `pipeline.yaml` + copia de spec | Agentes basados en Architect |
| `generic` | `SPEC.md` + `verify.sh` + copia de spec | Cualquier agente / uso manual |
| `claude-code` | `CLAUDE.md` + `.intake/tasks/` + `verify.sh` | Claude Code |
| `cursor` | `.cursor/rules/intake-spec.mdc` | Cursor |
| `kiro` | `requirements.md` + `design.md` + `tasks.md` (formato nativo) | Kiro |
| `copilot` | `.github/copilot-instructions.md` | GitHub Copilot |

Ver [Exportacion](exportacion.md) para detalles completos.

---

## Flujo de datos completo

```
.md / .json / .pdf / .docx / .html / .yaml / .txt / .png / URLs
                           |
                   [ SOURCE RESOLUTION ]
                   (parse_source → file, url, stdin, text)
                           |
                      [ INGEST ]
                      (11 parsers via plugin discovery)
                           |
                   list[ParsedContent]
                           |
                  [ COMPLEXITY CLASSIFICATION ]
                  (quick / standard / enterprise)
                           |
                      [ ANALYZE ]
                      (3 LLM calls)
                           |
                     AnalysisResult
                           |
                  [ ADAPTIVE GENERATE ]
                  (2-6 templates segun modo)
                           |
              specs/mi-feature/
              ├── requirements.md    (standard, enterprise)
              ├── design.md          (standard, enterprise)
              ├── tasks.md           (siempre)
              ├── acceptance.yaml    (standard, enterprise)
              ├── context.md         (siempre)
              ├── sources.md         (standard, enterprise)
              └── spec.lock.yaml
                           |
                      [ VERIFY ]         [ EXPORT ]
                           |                  |
                  VerificationReport     output/
                  (pass/fail/skip)       ├── pipeline.yaml  (architect)
                                         ├── SPEC.md        (generic)
                                         ├── verify.sh      (generic)
                                         ├── CLAUDE.md      (claude-code)
                                         ├── .cursor/rules/ (cursor)
                                         ├── .github/       (copilot)
                                         └── spec/          (copia)
                                                |
                                         [ FEEDBACK ]  (opcional)
                                                |
                                        FeedbackResult
                                        (sugerencias + enmiendas)

                                                |
                                         [ MCP SERVER ]  (opcional)
                                                |
                                        Agentes IA consumen specs
                                        via tools, resources, prompts
```

---

## MCP Server (opcional)

**Modulo:** `mcp/`
**Requiere LLM:** No (excepto `intake_feedback` tool)

### Que hace

Expone las specs como un servidor MCP (Model Context Protocol) para que cualquier agente IA compatible pueda consumirlas programaticamente. No es una fase del pipeline en si, sino una capa de consumo que se ubica despues del export.

### Que expone

| Tipo | Cantidad | Descripcion |
|------|----------|-------------|
| Tools | 7 | Operaciones sobre specs (show, verify, feedback, tasks, etc.) |
| Resources | 6 | Acceso directo a archivos spec via URIs `intake://specs/{name}/{section}` |
| Prompts | 2 | Templates estructurados para agentes (implement_next_task, verify_and_fix) |

### Transportes

| Transporte | Uso |
|-----------|-----|
| `stdio` | Agentes locales (Claude Code, Claude Desktop). Default. |
| `sse` | Agentes remotos via HTTP (Server-Sent Events). |

Ver [MCP Server](mcp-server.md) para documentacion completa.

---

## Watch Mode (opcional)

**Modulo:** `watch/`
**Requiere LLM:** No

### Que hace

Monitorea el directorio del proyecto y re-ejecuta automaticamente los checks de verificacion cuando detecta cambios en archivos. Complementa la fase de Verify con un ciclo continuo durante el desarrollo.

### Flujo

```
                    [ WATCH ]
                        |
    Detecta cambios --> Filtra ignorados --> Re-ejecuta verify --> Muestra resultado
         ^                                                              |
         └──────────────────────────────────────────────────────────────┘
```

Usa `watchfiles` (Rust-based) con debouncing configurable y patrones de exclusion.

Ver [Watch Mode](watch-mode.md) para documentacion completa.

---

## Feedback Loop (opcional)

**Modulo:** `feedback/`
**Requiere LLM:** Si (async via `litellm.acompletion`)

### Que hace

Cierra el ciclo entre verificacion e implementacion. Cuando checks fallan, analiza las causas y sugiere correcciones tanto a la implementacion como a la spec.

### Flujo

```
VerificationReport (checks fallidos)
         |
   [ ANALYZE FAILURES ]     (llamada LLM)
         |
   FeedbackResult
   ├── FailureAnalysis[]     (causa raiz + sugerencia por cada fallo)
   ├── SpecAmendment[]       (enmiendas propuestas a la spec)
   ├── summary               (resumen general)
   └── estimated_effort      (small / medium / large)
         |
   [ APPLY? ]               (si --apply o auto_amend_spec)
         |
   Spec actualizada
```

### Componentes

| Componente | Que hace |
|-----------|---------|
| `FeedbackAnalyzer` | Analiza fallos con LLM, produce `FeedbackResult` |
| `SuggestionFormatter` | Formatea sugerencias para terminal o agente (generic, claude-code, cursor) |
| `SpecUpdater` | Preview y aplicacion de enmiendas a los archivos spec |

### Modelo de datos

| Dataclass | Campos principales |
|-----------|-------------------|
| `FailureAnalysis` | check_name, root_cause, suggestion, severity, affected_tasks, spec_amendment |
| `SpecAmendment` | target_file, section, action (add/modify/remove), content |
| `FeedbackResult` | failures, summary, estimated_effort, total_cost |
| `AmendmentPreview` | amendment, current_content, proposed_content, applicable, reason |
| `ApplyResult` | applied, skipped, details |

Ver [Feedback](feedback.md) para documentacion completa.
