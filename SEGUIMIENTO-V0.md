# intake V0 — Seguimiento de Implementación

> Tracking detallado del progreso de implementación del MVP (V0).
> Actualizado: 2026-03-02 (Week 4 completada)

---

## Estado General

| Semana | Fase | Estado | Tests | Coverage |
|--------|------|--------|-------|----------|
| **Week 1** | Scaffolding + Parsers | **Completada** | 135/135 | 79% |
| **Week 2** | LLM Analysis + Generation | **Completada** | 217/217 | 85% |
| **Week 3** | Verification + Export + Features | **Completada** | 289/289 | 84% |
| **Week 4** | Documentation + Polish + Release | **Completada** | 313/313 | 83% |

---

## Week 1 — Scaffolding + Parsers

### Day 1: Scaffolding + Doctor ✅

| Componente | Archivo | Estado | Notas |
|------------|---------|--------|-------|
| pyproject.toml | `pyproject.toml` | ✅ | PEP 621, hatchling, todas las deps definidas |
| Package init | `src/intake/__init__.py` | ✅ | `__version__ = "0.1.0"` |
| Module runner | `src/intake/__main__.py` | ✅ | `python -m intake` funciona |
| Config schema | `src/intake/config/schema.py` | ✅ | 6 modelos Pydantic v2: LLM, Project, Spec, Verification, Export, Security |
| Config defaults | `src/intake/config/defaults.py` | ✅ | Constantes centralizadas, sin magic strings |
| Config presets | `src/intake/config/presets.py` | ✅ | minimal / standard / enterprise |
| Config loader | `src/intake/config/loader.py` | ✅ | Merge 4 capas: defaults → preset → .intake.yaml → CLI flags |
| CLI principal | `src/intake/cli.py` | ✅ | 8 comandos Click: init, add, verify, export, show, list, diff, doctor |
| Doctor checks | `src/intake/doctor/checks.py` | ✅ | Python version, API keys, deps opcionales, config YAML |
| Logging setup | `src/intake/utils/logging.py` | ✅ | structlog con ConsoleRenderer/JSONRenderer |
| `pip install -e .` | — | ✅ | Instalación en modo desarrollo funciona |
| `intake --version` | — | ✅ | Responde `intake, version 0.1.0` |
| `intake doctor` | — | ✅ | Tabla Rich con 9 checks, exit code semántico |

### Day 2: Parser Base + Text Parsers ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| ParsedContent | `src/intake/ingest/base.py` | ✅ | 100% | Dataclass con text, format, source, metadata, sections, relations |
| Parser Protocol | `src/intake/ingest/base.py` | ✅ | 100% | `@runtime_checkable`, can_parse + parse |
| Exceptions | `src/intake/ingest/base.py` | ✅ | 100% | IngestError, ParseError, UnsupportedFormatError |
| ParserRegistry | `src/intake/ingest/registry.py` | ✅ | 92% | Auto-detección por extensión + contenido |
| MarkdownParser | `src/intake/ingest/markdown.py` | ✅ | 92% | Soporta front matter YAML, extrae secciones por headings |
| PlaintextParser | `src/intake/ingest/plaintext.py` | ✅ | 97% | Soporta .txt, stdin ('-'), extrae párrafos |
| YamlInputParser | `src/intake/ingest/yaml_input.py` | ✅ | 96% | Soporta .yaml/.yml/.json, secciones por top-level keys |

### Day 3: PDF + DOCX Parsers ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| PdfParser | `src/intake/ingest/pdf.py` | ✅ | 14%* | pdfplumber, extrae texto + tablas como Markdown |
| DocxParser | `src/intake/ingest/docx.py` | ✅ | 12%* | python-docx, extrae texto + tablas + metadata + secciones por headings |

> *Coverage bajo porque faltan fixtures reales (.pdf y .docx). El código está completo y probado manualmente.

### Day 4: Jira + Confluence Parsers ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| JiraParser | `src/intake/ingest/jira.py` | ✅ | 86% | Soporta formato API `{"issues":[...]}` y formato lista `[{"key":...}]` |
| ConfluenceParser | `src/intake/ingest/confluence.py` | ✅ | 81% | BS4 + markdownify, detecta Confluence por markers en HTML |

**Datos extraídos por JiraParser:**
- Summary, description, priority, status, labels
- Comments (últimos 5 por issue, truncados a 500 chars)
- Issue links (blocks, depends on, relates to)
- Soporte para ADF (Atlassian Document Format) en comments

**Datos extraídos por ConfluenceParser:**
- Texto limpio convertido a Markdown
- Secciones por headings
- Tablas HTML → Markdown
- Metadata de la página (title, author, date)

### Day 5: Image Parser + Auto-detection avanzada ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| ImageParser | `src/intake/ingest/image.py` | ✅ | 100% | Stub con VisionCallable inyectable, base64 encoding |
| JSON subtype detection | `src/intake/ingest/registry.py` | ✅ | 92% | Detecta Jira vs JSON genérico |
| HTML subtype detection | `src/intake/ingest/registry.py` | ✅ | 92% | Detecta Confluence vs HTML genérico |
| Default registry | `src/intake/ingest/registry.py` | ✅ | 92% | `create_default_registry()` con 8 parsers |

### Utils implementados ✅

| Componente | Archivo | Estado | Coverage |
|------------|---------|--------|----------|
| file_detect | `src/intake/utils/file_detect.py` | ✅ | 100% |
| project_detect | `src/intake/utils/project_detect.py` | ✅ | 93% |
| cost tracker | `src/intake/utils/cost.py` | ✅ | 100% |
| logging | `src/intake/utils/logging.py` | ✅ | 100% |

### Tests y Fixtures ✅

**135 tests, 0 failures, 79% coverage global**

| Test file | Tests | Estado |
|-----------|-------|--------|
| `tests/test_cli.py` | 7 | ✅ |
| `tests/test_config/test_schema.py` | 7 | ✅ |
| `tests/test_config/test_presets.py` | 6 | ✅ |
| `tests/test_config/test_loader.py` | 8 | ✅ |
| `tests/test_doctor/test_checks.py` | 9 | ✅ |
| `tests/test_ingest/test_markdown.py` | 10 | ✅ |
| `tests/test_ingest/test_plaintext.py` | 8 | ✅ |
| `tests/test_ingest/test_yaml_input.py` | 8 | ✅ |
| `tests/test_ingest/test_jira.py` | 10 | ✅ |
| `tests/test_ingest/test_confluence.py` | 8 | ✅ |
| `tests/test_ingest/test_image.py` | 8 | ✅ |
| `tests/test_ingest/test_registry.py` | 17 | ✅ |
| `tests/test_utils/test_file_detect.py` | 16 | ✅ |
| `tests/test_utils/test_project_detect.py` | 8 | ✅ |
| `tests/test_utils/test_cost.py` | 5 | ✅ |

**Fixtures creados:**

| Fixture | Formato | Propósito |
|---------|---------|-----------|
| `simple_spec.md` | Markdown | Spec OAuth2 con front matter YAML, headings, requirements |
| `slack_thread.txt` | Plaintext | Thread de Slack sobre password reset (multi-persona) |
| `structured_reqs.yaml` | YAML | Requirements estructurados con IDs, prioridades, acceptance criteria |
| `jira_export.json` | Jira JSON (API) | 3 issues con comments, links, labels, priorities |
| `jira_export_multi.json` | Jira JSON (list) | 2 issues en formato lista |
| `confluence_page.html` | Confluence HTML | RFC con tablas, headings, metadata, markers de Confluence |
| `wireframe.png` | Image | PNG mínimo para tests de ImageParser |

---

## Week 2 — LLM Analysis + Generation ✅

### Day 6: LLM Adapter ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| LLMAdapter | `src/intake/llm/adapter.py` | ✅ | 90% | Async completion, retry con backoff exponencial, cost tracking, budget enforcement |
| LLMError | `src/intake/llm/adapter.py` | ✅ | 90% | Excepciones con reason + suggestion |
| CostLimitError | `src/intake/llm/adapter.py` | ✅ | 90% | Acumulado vs límite, mensaje descriptivo |
| APIKeyMissingError | `src/intake/llm/adapter.py` | ✅ | 90% | Indica qué env var falta y cómo setearla |

### Day 7: Analysis Pipeline Core ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| Data models (10) | `src/intake/analyze/models.py` | ✅ | 100% | Requirement, Conflict, OpenQuestion, RiskItem, TechDecision, TaskItem, FileAction, AcceptanceCheck, DesignResult, AnalysisResult |
| System prompts (3) | `src/intake/analyze/prompts.py` | ✅ | 100% | EXTRACTION_PROMPT, RISK_ASSESSMENT_PROMPT, DESIGN_PROMPT |
| Extraction parser | `src/intake/analyze/extraction.py` | ✅ | 97% | JSON → typed AnalysisResult |
| Analyzer orchestrator | `src/intake/analyze/analyzer.py` | ✅ | 100% | Extraction → dedup → validate → risk → design |

### Day 8: Advanced Analysis ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| Deduplication | `src/intake/analyze/dedup.py` | ✅ | 98% | Jaccard word similarity, threshold 0.75 |
| Conflict validation | `src/intake/analyze/conflicts.py` | ✅ | 100% | Filtra conflictos incompletos |
| Questions validation | `src/intake/analyze/questions.py` | ✅ | 80% | Filtra preguntas incompletas |
| Risk assessment | `src/intake/analyze/risks.py` | ✅ | 93% | Parsea JSON de riesgos a RiskItem |
| Design parser | `src/intake/analyze/design.py` | ✅ | 97% | JSON → DesignResult con tasks y checks |

### Day 9-10: Generate Module + Templates ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| SpecBuilder | `src/intake/generate/spec_builder.py` | ✅ | 88% | Orquesta 6 templates + lock |
| SpecLock | `src/intake/generate/lock.py` | ✅ | 98% | SHA-256 hashing, staleness detection, YAML I/O |
| requirements.md.j2 | `src/intake/templates/` | ✅ | — | FR, NFR, conflicts, open questions |
| design.md.j2 | `src/intake/templates/` | ✅ | — | Components, files, tech decisions |
| tasks.md.j2 | `src/intake/templates/` | ✅ | — | Summary table + detailed task sections |
| acceptance.yaml.j2 | `src/intake/templates/` | ✅ | — | Checks por tipo: command, files_exist, pattern_* |
| context.md.j2 | `src/intake/templates/` | ✅ | — | Project info, stack, risks summary |
| sources.md.j2 | `src/intake/templates/` | ✅ | — | Source list + requirement traceability |

### Tests Week 2 ✅

**82 tests nuevos, 217 total, 0 failures, 85% coverage global**

| Test file | Tests | Estado |
|-----------|-------|--------|
| `tests/test_analyze/test_analyzer.py` | 7 | ✅ |
| `tests/test_analyze/test_extraction.py` | 9 | ✅ |
| `tests/test_analyze/test_dedup.py` | 14 | ✅ |
| `tests/test_analyze/test_conflicts.py` | 7 | ✅ |
| `tests/test_analyze/test_design.py` | 9 | ✅ |
| `tests/test_analyze/test_risks.py` | 7 | ✅ |
| `tests/test_analyze/test_llm_adapter.py` | 8 | ✅ |
| `tests/test_generate/test_spec_builder.py` | 11 | ✅ |
| `tests/test_generate/test_lock.py` | 10 | ✅ |

### Coverage por módulo (acumulado Week 1 + Week 2)

| Módulo | Stmts | Miss | Coverage |
|--------|-------|------|----------|
| `analyze/` | 283 | 8 | **97%** |
| `config/` | 152 | 8 | **95%** |
| `generate/` | 110 | 7 | **94%** |
| `llm/` | 101 | 10 | **90%** |
| `doctor/` | 64 | 3 | **95%** |
| `ingest/` | 576 | 188 | **67%** |
| `utils/` | 88 | 2 | **98%** |
| `cli.py` | 101 | 15 | **85%** |
| **TOTAL** | **1657** | **255** | **85%** |

> Nota: `ingest/pdf.py` (14%) y `ingest/docx.py` (12%) bajan el promedio de ingest porque requieren fixtures binarios reales (.pdf, .docx) que no se han generado aún.

---

## Week 3 — Verification + Export + Features ✅

### Day 11: Verification Engine ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| VerificationEngine | `src/intake/verify/engine.py` | ✅ | 88% | 4 check types: command, files_exist, pattern_present, pattern_absent |
| CheckResult | `src/intake/verify/engine.py` | ✅ | 88% | Dataclass con id, name, passed, required, output, error, duration_ms |
| VerificationReport | `src/intake/verify/engine.py` | ✅ | 88% | Aggregated results + exit_code property (0/1) |
| VerifyError | `src/intake/verify/engine.py` | ✅ | 88% | Custom exception con reason + suggestion |

### Day 12: Reporters + Exporters ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| TerminalReporter | `src/intake/verify/reporter.py` | ✅ | 95% | Rich table con colores |
| JsonReporter | `src/intake/verify/reporter.py` | ✅ | 95% | JSON machine-readable |
| JunitReporter | `src/intake/verify/reporter.py` | ✅ | 95% | JUnit XML para CI |
| Reporter Protocol | `src/intake/verify/reporter.py` | ✅ | 95% | `@runtime_checkable` |
| Exporter Protocol | `src/intake/export/base.py` | ✅ | 100% | `@runtime_checkable` |
| ExporterRegistry | `src/intake/export/registry.py` | ✅ | 100% | Format-based dispatch |
| ArchitectExporter | `src/intake/export/architect.py` | ✅ | 93% | pipeline.yaml + spec copy |
| GenericExporter | `src/intake/export/generic.py` | ✅ | 95% | SPEC.md + verify.sh + spec copy |

### Day 13: CLI Complete ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| `init` command | `src/intake/cli.py` | ✅ | 66% | Full pipeline: ingest → analyze → generate → export |
| `add` command | `src/intake/cli.py` | ✅ | 66% | Incremental source addition |
| `verify` command | `src/intake/cli.py` | ✅ | 66% | Runs acceptance checks, semantic exit codes |
| `export` command | `src/intake/cli.py` | ✅ | 66% | Exports to architect/generic format |
| `show` command | `src/intake/cli.py` | ✅ | 66% | Spec summary from lock file |
| `list` command | `src/intake/cli.py` | ✅ | 66% | Lists all specs in directory |
| `diff` command | `src/intake/cli.py` | ✅ | 66% | Compares two spec versions |
| `_slugify` helper | `src/intake/cli.py` | ✅ | 66% | Description → directory name |

### Day 14: Spec Differ ✅

| Componente | Archivo | Estado | Coverage | Notas |
|------------|---------|--------|----------|-------|
| SpecDiffer | `src/intake/diff/differ.py` | ✅ | 95% | Compares requirements, tasks, acceptance by ID |
| DiffEntry | `src/intake/diff/differ.py` | ✅ | 95% | section, change_type, item_id, old/new values |
| SpecDiff | `src/intake/diff/differ.py` | ✅ | 95% | Properties: added, removed, modified, has_changes |
| DiffError | `src/intake/diff/differ.py` | ✅ | 95% | Custom exception con reason + suggestion |

### Tests Week 3 ✅

**72 tests nuevos, 289 total, 0 failures, 84% coverage global**

| Test file | Tests | Estado |
|-----------|-------|--------|
| `tests/test_verify/test_engine.py` | 15 | ✅ |
| `tests/test_verify/test_reporter.py` | 11 | ✅ |
| `tests/test_export/test_architect.py` | 8 | ✅ |
| `tests/test_export/test_generic.py` | 8 | ✅ |
| `tests/test_export/test_registry.py` | 6 | ✅ |
| `tests/test_diff/test_differ.py` | 12 | ✅ |
| `tests/test_cli.py` | 19 (+12) | ✅ |

### Coverage por módulo (acumulado Week 1 + 2 + 3)

| Módulo | Stmts | Miss | Coverage |
|--------|-------|------|----------|
| `verify/` | 213 | 21 | **90%** |
| `export/` | 192 | 9 | **95%** |
| `diff/` | 114 | 5 | **96%** |
| `analyze/` | 283 | 8 | **97%** |
| `config/` | 152 | 8 | **95%** |
| `generate/` | 110 | 7 | **94%** |
| `llm/` | 101 | 10 | **90%** |
| `doctor/` | 64 | 3 | **95%** |
| `ingest/` | 576 | 188 | **67%** |
| `utils/` | 89 | 2 | **98%** |
| `cli.py` | 325 | 110 | **66%** |
| **TOTAL** | **2397** | **382** | **84%** |

> Nota: `cli.py` tiene 66% porque `init` y `add` requieren LLM mock completo. `ingest/pdf.py` (14%) y `ingest/docx.py` (12%) bajan el promedio de ingest porque requieren fixtures binarios reales.

## Week 4 — Polish + Release ✅

### .intake.yaml.example ✅

| Componente | Archivo | Estado | Notas |
|------------|---------|--------|-------|
| Config example | `.intake.yaml.example` | ✅ | Documentado con todas las opciones, comentarios en inglés |

### Examples Directory ✅

| Componente | Directorio | Estado | Notas |
|------------|------------|--------|-------|
| From Markdown | `examples/from-markdown/` | ✅ | README + requirements.md (OAuth2 spec) |
| From Jira | `examples/from-jira/` | ✅ | README + jira-export.json (3 issues) |
| From Scratch | `examples/from-scratch/` | ✅ | README + free-text notes |
| Multi-source | `examples/multi-source/` | ✅ | README + 3 source files (Markdown + JSON + text) |

### Error Hardening ✅

| Componente | Archivo | Estado | Notas |
|------------|---------|--------|-------|
| EmptySourceError | `src/intake/ingest/base.py` | ✅ | Excepción específica para archivos vacíos |
| FileTooLargeError | `src/intake/ingest/base.py` | ✅ | Excepción con límite configurable (50MB default) |
| validate_file_readable | `src/intake/ingest/base.py` | ✅ | Valida existencia, tamaño, no-directorio |
| read_text_safe | `src/intake/ingest/base.py` | ✅ | UTF-8 → latin-1 fallback, empty check |
| 8 parsers actualizados | `src/intake/ingest/*.py` | ✅ | Todos usan validate_file_readable + read_text_safe |
| Hardening tests | `tests/test_ingest/test_hardening.py` | ✅ | 16 tests: empty files, encoding, size limits, directories |

### Doctor --fix ✅

| Componente | Archivo | Estado | Notas |
|------------|---------|--------|-------|
| fix() method | `src/intake/doctor/checks.py` | ✅ | Auto-instala paquetes faltantes, crea config |
| FixResult | `src/intake/doctor/checks.py` | ✅ | Dataclass con name, success, message |
| _find_pip() | `src/intake/doctor/checks.py` | ✅ | Detecta pip3.12, pip3, o pip |
| IMPORT_TO_PIP | `src/intake/doctor/checks.py` | ✅ | Mapeo de imports a nombres de paquetes PyPI |
| CLI --fix flag | `src/intake/cli.py` | ✅ | Wired con display de resultados Rich |
| Fix tests | `tests/test_doctor/test_checks.py` | ✅ | 8 tests nuevos (17 total en el archivo) |

### Ruff Lint Fixes ✅

| Categoría | Cantidad | Notas |
|-----------|----------|-------|
| Auto-fixed (--unsafe-fixes) | 68 issues | TC001/TC003, F401, I001, SIM103, RUF022 |
| Manual fixes (E501) | ~12 | Líneas largas en tests y analyzer |
| Manual fixes (SIM117) | ~4 | Parenthesized context managers en test_llm_adapter |
| Manual fixes (RUF043) | ~4 | Raw regex strings en tests |
| **Total** | **0 errors** | `ruff check src/ tests/` → All checks passed! |

### Mypy Strict Fixes ✅

| Archivo | Errores | Fix aplicado |
|---------|---------|--------------|
| `analyze/extraction.py` | 3 | `_get_list` filtra isinstance(dict), nuevo `_get_str_list` |
| `analyze/design.py` | 4 | isinstance guards para int() overloads, `_get_list` fix |
| `analyze/conflicts.py` | 1 | `return bool(...)` en vez de `return str.strip()` |
| `analyze/risks.py` | 2 | bool return fix + `_get_list` fix |
| `analyze/questions.py` | 1 | bool return fix |
| `analyze/analyzer.py` | 5 | Return types, isinstance guards, DesignResult import |
| `ingest/jira.py` | 2 | isinstance narrowing, removed type: ignore |
| `ingest/docx.py` | 3 | `Any` types, removed isinstance(doc, Document) guards |
| `ingest/confluence.py` | 1 | `attrs=selector` en vez de `**kwargs` para bs4 |
| `ingest/pdf.py` | 2 | `Any` types, row variable fix |
| `llm/adapter.py` | 1 | Removed unused type: ignore |
| `verify/engine.py` | 1 | isinstance narrowing for tags and patterns |
| **Total** | **26 → 0** | `mypy src/ --strict` → Success: 51 source files |

### Tests Week 4 ✅

**24 tests nuevos, 313 total, 0 failures, 83% coverage global**

| Test file | Tests | Estado |
|-----------|-------|--------|
| `tests/test_ingest/test_hardening.py` | 16 | ✅ (nuevo) |
| `tests/test_doctor/test_checks.py` | 17 (+8) | ✅ |

### Coverage por módulo (acumulado Week 1 + 2 + 3 + 4)

| Módulo | Stmts | Miss | Coverage |
|--------|-------|------|----------|
| `verify/` | 221 | 22 | **90%** |
| `export/` | 192 | 9 | **95%** |
| `diff/` | 114 | 5 | **96%** |
| `analyze/` | 286 | 8 | **97%** |
| `config/` | 151 | 8 | **95%** |
| `generate/` | 110 | 7 | **94%** |
| `llm/` | 98 | 9 | **91%** |
| `doctor/` | 125 | 21 | **83%** |
| `ingest/` | 638 | 195 | **69%** |
| `utils/` | 89 | 2 | **98%** |
| `cli.py` | 394 | 130 | **67%** |
| **TOTAL** | **2518** | **416** | **83%** |

> Nota: `ingest/pdf.py` (15%) e `ingest/docx.py` (14%) bajan el promedio de ingest porque requieren fixtures binarios reales. `cli.py` tiene 67% porque `init` y `add` requieren LLM mock completo.

### Quality Gates Week 4 ✅

| Gate | Estado | Resultado |
|------|--------|-----------|
| `python3.12 -m pytest tests/ -q` | ✅ | 313 passed in 20s |
| `python3.12 -m ruff check src/ tests/` | ✅ | All checks passed! |
| `python3.12 -m mypy src/ --strict` | ✅ | Success: no issues found in 51 source files |
| PyPI release | ⬜ | Controlado por el usuario |

---

## Decisiones Técnicas Tomadas

1. **structlog en tests**: Se usa `JSONRenderer` + `_NullWriter` custom sink con `cache_logger_on_first_use=False`. Se descartó `StringIO` y `os.devnull` porque ambos se corrompen al interactuar con `CliRunner` de Click.

2. **ImageParser desacoplado del LLM**: Acepta un `VisionCallable` inyectable en lugar de importar directamente de `llm/`. Stub por defecto retorna placeholder.

3. **JiraParser soporta ADF**: Extrae texto plano de Atlassian Document Format (JSON anidado) en comments.

4. **Registry fallback a plaintext**: Si no hay parser para un formato detectado pero existe un parser `plaintext` registrado, se usa como fallback con un warning.

5. **Config merge con `model_copy(update=...)`**: Se usa el método nativo de Pydantic v2 para merges inmutables en cada capa de configuración.

6. **LLM lazy import**: `litellm.acompletion` se importa dentro de `_call_llm()` (no a nivel de módulo) para permitir que los tests parcheen sin problemas y para evitar cargar litellm cuando no se necesita.

7. **Dedup threshold a 0.75**: Jaccard word similarity con threshold de 0.85 era demasiado estricto para comparaciones a nivel de palabras. Se bajó a 0.75 que es más práctico para títulos cortos de requirements.

8. **Templates Jinja2 con lstrip/trim**: Se usan `trim_blocks=True` y `lstrip_blocks=True` en el Environment de Jinja2 para evitar líneas en blanco innecesarias en el output.

9. **Protocol over ABC para exporters**: Tanto `Exporter` como `Reporter` usan `typing.Protocol` con `@runtime_checkable`, igual que `Parser`. Esto permite structural subtyping sin herencia.

10. **Verify check pattern**: El engine procesa 4 tipos de checks (command, files_exist, pattern_present, pattern_absent) con timeout configurable. `pattern_present/absent` verifican ALL matching files, no any.

11. **Generic exporter con verify.sh**: Genera un script bash ejecutable con `set -euo pipefail` y función `check()` reutilizable. Hace `chmod +x` automático.

12. **Architect pipeline con final-verification**: El step final agrupa todos los command checks required de acceptance.yaml como verificación integral.

13. **CLI _slugify**: Convierte descripciones a slugs para nombres de directorio (lowercase, hyphens, max 50 chars).

14. **setup_logging con cache_logger_on_first_use=False**: Cambiado de `True` a `False` para compatibilidad con tests. Los module-level loggers necesitan reconfigurarse entre tests.
