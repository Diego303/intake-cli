# Feedback Loop

El feedback loop cierra el ciclo entre verificacion e implementacion. Cuando la verificacion detecta checks fallidos, el modulo `feedback` analiza las causas y sugiere correcciones.

```
VERIFY (checks fallan) --> FEEDBACK (analisis LLM) --> Sugerencias + Enmiendas a la spec
```

---

## Uso basico

```bash
# Analizar fallos y ver sugerencias
intake feedback specs/mi-feature/ -p .

# Con un reporte de verificacion existente
intake feedback specs/mi-feature/ --verify-report report.json

# Aplicar enmiendas a la spec automaticamente
intake feedback specs/mi-feature/ -p . --apply

# Sugerencias en formato para un agente especifico
intake feedback specs/mi-feature/ -p . --agent-format claude-code
```

### Que pasa internamente

1. Si no se proporciona `--verify-report`, ejecuta `intake verify` primero para generar un reporte JSON
2. Filtra los checks con estado `fail`
3. Carga la spec (requirements, design, tasks) como contexto
4. Envia los fallos + contexto al LLM para analisis de causa raiz
5. Genera un `FeedbackResult` con sugerencias estructuradas
6. Muestra las sugerencias en terminal (o las formatea para un agente)
7. Si `--apply` o `feedback.auto_amend_spec`, aplica las enmiendas propuestas a la spec

---

## Output

El comando muestra en terminal:

```
Feedback Analysis
=================

CRITICAL  check-api-tests
  Root cause: API endpoint /users/register not implemented yet
  Fix: Implement POST /users/register in src/api/routes.py
  Affected tasks: Task 2, Task 3
  Amendment: Modify requirements.md section FR-001

MAJOR  check-lint
  Root cause: Missing type hints in new modules
  Fix: Add type annotations to src/api/models.py
  Affected tasks: Task 1

Summary: 2 failures analyzed, 1 critical
Estimated effort: medium
Amendments: 1 proposed (use --apply to apply)
```

---

## Severidades

| Severidad | Significado |
|-----------|-------------|
| `critical` | Bloquea funcionalidad core. Debe resolverse primero. |
| `major` | Afecta funcionalidad importante. Alta prioridad. |
| `minor` | Mejora de calidad. Puede posponerse. |

---

## Enmiendas a la spec

Cuando el analisis identifica que la spec necesita ajustes, propone `SpecAmendment`:

```python
@dataclass
class SpecAmendment:
    target_file: str    # Archivo spec (ej: "requirements.md")
    section: str        # Seccion (ej: "FR-001")
    action: str         # "add", "modify", "remove"
    content: str        # Contenido propuesto
```

### Preview

Sin `--apply`, las enmiendas se muestran como propuestas:

```
Proposed amendments:
  [1] MODIFY requirements.md > FR-001
      Current: "Users must register with email"
      Proposed: "Users must register with email and password validation"

Use --apply to apply these amendments.
```

### Aplicacion automatica

Con `--apply` o `feedback.auto_amend_spec: true`:

```
Applied 1 amendment(s), skipped 0
  [OK] Modified requirements.md > FR-001
```

Las enmiendas que no se pueden aplicar (seccion no encontrada, archivo no existe) se saltan con un mensaje explicativo.

---

## Formatos de agente

El flag `--agent-format` formatea las sugerencias para un agente especifico:

| Formato | Descripcion |
|---------|-------------|
| `generic` | Markdown generico (default) |
| `claude-code` | Formato optimizado para Claude Code |
| `cursor` | Formato optimizado para Cursor |

```bash
# Guardar sugerencias formateadas
intake feedback specs/mi-feature/ -p . --agent-format claude-code > feedback.md
```

---

## Configuracion

```yaml
feedback:
  auto_amend_spec: false          # Aplicar enmiendas automaticamente (sin --apply)
  max_suggestions: 10             # Maximo de sugerencias por analisis
  include_code_snippets: true     # Incluir fragmentos de codigo en las sugerencias
```

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `auto_amend_spec` | bool | `false` | Si `true`, aplica enmiendas sin necesidad de `--apply`. |
| `max_suggestions` | int | `10` | Limita la cantidad de sugerencias del LLM. |
| `include_code_snippets` | bool | `true` | Pide al LLM incluir codigo en las sugerencias. |

---

## Modelo de datos

### FeedbackResult

```python
@dataclass
class FeedbackResult:
    failures: list[FailureAnalysis]     # Analisis por cada check fallido
    summary: str                        # Resumen general
    estimated_effort: str               # "small", "medium", "large"
    total_cost: float                   # Costo del analisis LLM (USD)

    @property
    def amendment_count(self) -> int: ...   # Enmiendas propuestas

    @property
    def critical_count(self) -> int: ...   # Fallos criticos
```

### FailureAnalysis

```python
@dataclass
class FailureAnalysis:
    check_name: str                         # Nombre del check fallido
    root_cause: str                         # Causa raiz identificada
    suggestion: str                         # Sugerencia de correccion
    category: str = "implementation_gap"    # Categoria del fallo
    severity: str = "major"                 # critical | major | minor
    affected_tasks: list[str] = []          # Tareas afectadas
    spec_amendment: SpecAmendment | None = None  # Enmienda propuesta
```

### SpecUpdater

```python
class SpecUpdater:
    def preview(result: FeedbackResult) -> list[AmendmentPreview]: ...
    def apply(result: FeedbackResult) -> ApplyResult: ...
```

- `preview()` retorna previews sin modificar archivos
- `apply()` modifica los archivos spec y retorna conteos

---

## Uso programatico

```python
from intake.feedback import FeedbackAnalyzer, SuggestionFormatter, SpecUpdater
from intake.config.schema import IntakeConfig
from intake.llm.adapter import LLMAdapter

# Analizar
analyzer = FeedbackAnalyzer(config=IntakeConfig(), llm=llm_adapter)
result = await analyzer.analyze(
    verify_report=report_json,
    spec_dir="specs/mi-feature/",
)

# Formatear sugerencias
formatter = SuggestionFormatter()
markdown = formatter.format(result, agent_format="claude-code")

# Aplicar enmiendas
updater = SpecUpdater(spec_dir="specs/mi-feature/")
previews = updater.preview(result)
apply_result = updater.apply(result)
```

---

## Costos

El feedback loop hace una llamada LLM por analisis. El costo depende del tamano de la spec y la cantidad de checks fallidos:

| Escenario | Costo aproximado |
|-----------|------------------|
| Pocos fallos, spec pequena | ~$0.01-0.03 |
| Muchos fallos, spec mediana | ~$0.03-0.10 |
| Spec grande + enterprise | ~$0.10-0.20 |

El costo se reporta en `FeedbackResult.total_cost`.
