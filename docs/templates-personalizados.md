# Templates personalizados

Guia para personalizar los templates Jinja2 que intake usa para generar archivos spec y exportaciones.

---

## Como funciona

intake usa 17 templates Jinja2 para generar todos sus archivos de salida. El sistema de templates tiene **dos niveles de prioridad**:

1. **Templates de usuario** (en `.intake/templates/` del proyecto) — prioridad alta
2. **Templates built-in** (incluidos en el paquete intake) — fallback

Si colocas un archivo con el mismo nombre que un template built-in en `.intake/templates/`, tu version se usa automaticamente en lugar del built-in. Esto permite personalizar el formato de cualquier archivo generado sin modificar intake.

```
mi-proyecto/
├── .intake/
│   └── templates/               # Tus overrides
│       ├── requirements.md.j2   # Sobreescribe el template de requisitos
│       └── verify_sh.j2         # Sobreescribe el template de verify.sh
└── .intake.yaml
```

---

## Configuracion

```yaml
# .intake.yaml
templates:
  user_dir: ".intake/templates"   # Directorio de templates de usuario (default)
  warn_on_override: true          # Log cuando un template built-in es sobreescrito (default)
```

| Campo | Default | Descripcion |
|-------|---------|-------------|
| `user_dir` | `.intake/templates` | Path relativo al proyecto donde buscar templates de usuario |
| `warn_on_override` | `true` | Emitir log `template_override` cuando se detecta un override |

---

## Templates disponibles

### Templates de spec (generacion)

Usados por `intake init` y `intake add` para generar los 6 archivos spec:

| Template | Archivo generado | Descripcion |
|----------|-----------------|-------------|
| `requirements.md.j2` | `requirements.md` | Requisitos funcionales y no funcionales |
| `design.md.j2` | `design.md` | Diseno tecnico: componentes, archivos, decisiones |
| `tasks.md.j2` | `tasks.md` | Tareas de implementacion con tabla resumen |
| `acceptance.yaml.j2` | `acceptance.yaml` | Checks de aceptacion en YAML |
| `context.md.j2` | `context.md` | Contexto del proyecto para agentes IA |
| `sources.md.j2` | `sources.md` | Trazabilidad requisito-a-fuente |

### Templates de exportacion

Usados por `intake export -f <formato>`:

| Template | Exporter | Archivo generado |
|----------|----------|-----------------|
| `claude_md.j2` | claude-code | Seccion `## intake Spec` en `CLAUDE.md` |
| `claude_task.md.j2` | claude-code | `TASK-NNN.md` individuales |
| `verify_sh.j2` | claude-code, generic | `verify.sh` ejecutable |
| `cursor_rules.mdc.j2` | cursor | `.cursor/rules/intake-spec.mdc` |
| `kiro_requirements.md.j2` | kiro | `requirements.md` formato Kiro |
| `kiro_design.md.j2` | kiro | `design.md` formato Kiro |
| `kiro_tasks.md.j2` | kiro | `tasks.md` formato Kiro |
| `copilot_instructions.md.j2` | copilot | `.github/copilot-instructions.md` |
| `feedback.md.j2` | feedback | Reporte de feedback |

### Templates de CI

Usados por `intake export-ci`:

| Template | Plataforma | Archivo generado |
|----------|-----------|-----------------|
| `gitlab_ci.yml.j2` | GitLab | `.gitlab-ci.yml` |
| `github_actions.yml.j2` | GitHub | `.github/workflows/intake-verify.yml` |

---

## Variables disponibles por template

### requirements.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `functional_requirements` | `list[dict]` | Requisitos funcionales. Cada uno tiene: `id`, `title`, `description`, `priority`, `source`, `acceptance_criteria` (list) |
| `non_functional_requirements` | `list[dict]` | Requisitos no funcionales (misma estructura) |
| `conflicts` | `list[dict]` | Conflictos detectados. Cada uno: `id`, `description`, `source_a`, `source_b`, `severity`, `recommendation` |
| `open_questions` | `list[dict]` | Preguntas abiertas. Cada una: `id`, `question`, `context`, `source`, `recommendation` |

### design.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `components` | `list[str]` | Nombres de componentes de arquitectura |
| `files_to_create` | `list[dict]` | Archivos a crear. Cada uno: `path`, `description` |
| `files_to_modify` | `list[dict]` | Archivos a modificar. Cada uno: `path`, `description` |
| `tech_decisions` | `list[dict]` | Decisiones tecnicas. Cada una: `decision`, `justification`, `requirement` |
| `dependencies` | `list[str]` | Dependencias del proyecto |

### tasks.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `tasks` | `list[dict]` | Tareas de implementacion. Cada una: `id`, `title`, `description`, `status`, `estimated_minutes`, `dependencies` (list), `files` (list), `checks` (list) |

### acceptance.yaml.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `checks` | `list[dict]` | Checks de aceptacion. Cada uno: `id`, `name`, `type`, `required`, `tags` (list), `command` (si type=command), `paths` (si type=files_exist), `glob` y `patterns` (si type=pattern_*) |

### context.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `project_name` | `str` | Nombre del proyecto |
| `language` | `str` | Idioma de la spec |
| `stack` | `list[str]` | Tech stack del proyecto |
| `conventions` | `dict[str, str]` | Convenciones del proyecto |
| `functional_count` | `int` | Cantidad de requisitos funcionales |
| `non_functional_count` | `int` | Cantidad de requisitos no funcionales |
| `question_count` | `int` | Preguntas abiertas |
| `conflict_count` | `int` | Conflictos detectados |
| `risk_count` | `int` | Riesgos identificados |
| `risks` | `list[dict]` | Riesgos. Cada uno: `id`, `category`, `probability`, `impact`, `description` |
| `component_count` | `int` | Componentes de arquitectura |
| `files_to_create_count` | `int` | Archivos a crear |
| `files_to_modify_count` | `int` | Archivos a modificar |
| `task_count` | `int` | Total de tareas |
| `check_count` | `int` | Total de checks |

### sources.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `sources` | `list[dict]` | Fuentes usadas. Cada una: `source`, `format`, `word_count` |
| `all_requirements` | `list[dict]` | Todos los requisitos con `id`, `title`, `source` |
| `conflicts` | `list[dict]` | Conflictos con fuentes |

### claude_md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `spec_name` | `str` | Nombre de la spec |
| `context_summary` | `str` | Resumen del contexto del proyecto |
| `requirements_count` | `int` | Cantidad de requisitos |
| `design_summary` | `str` | Resumen del diseno |
| `tasks` | `list[dict]` | Tareas con `id`, `title`, `status` |
| `acceptance_count` | `int` | Cantidad de checks |
| `spec_files` | `list[str]` | Nombres de archivos spec |

### claude_task.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `task` | `dict` | Tarea individual con `id`, `title`, `status`, `description`, `checks` (list) |
| `context_summary` | `str` | Resumen del contexto |

### verify_sh.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `spec_name` | `str` | Nombre de la spec |
| `checks` | `list[dict]` | Checks de tipo command. Cada uno: `name`, `command` |

### cursor_rules.mdc.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `spec_name` | `str` | Nombre de la spec |
| `context_summary` | `str` | Resumen del contexto |
| `requirements_count` | `int` | Cantidad de requisitos |
| `requirements_summary` | `str` | Resumen de requisitos |
| `design_summary` | `str` | Resumen del diseno |
| `tasks` | `list[dict]` | Tareas con `id`, `title`, `status`, `description` |
| `acceptance_checks` | `list[dict]` | Checks con `name`, `type`, `command`, `pattern` |

### kiro_requirements.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `spec_name` | `str` | Nombre de la spec |
| `requirements` | `list[dict]` | Requisitos con `id`, `title`, `description`, `acceptance_criteria` (list) |

### kiro_design.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `spec_name` | `str` | Nombre de la spec |
| `design_content` | `str` | Contenido del diseno |

### kiro_tasks.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `spec_name` | `str` | Nombre de la spec |
| `tasks` | `list[dict]` | Tareas con `id`, `title`, `status`, `description`, `checks` (list) |

### copilot_instructions.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `spec_name` | `str` | Nombre de la spec |
| `context_summary` | `str` | Resumen del contexto |
| `requirements_count` | `int` | Cantidad de requisitos |
| `requirements_summary` | `str` | Resumen de requisitos |
| `design_summary` | `str` | Resumen del diseno |
| `tasks` | `list[dict]` | Tareas con `id`, `title`, `status`, `description` |
| `acceptance_checks` | `list[dict]` | Checks con `name`, `command`, `pattern` |

### feedback.md.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `result` | `dict` | Resultado del analisis. Tiene: `failures` (list), `estimated_effort`, `summary` |
| `result.failures[].check_name` | `str` | Nombre del check fallido |
| `result.failures[].severity` | `str` | Severidad |
| `result.failures[].category` | `str` | Categoria |
| `result.failures[].root_cause` | `str` | Causa raiz |
| `result.failures[].suggestion` | `str` | Sugerencia de correccion |
| `result.failures[].affected_tasks` | `list[str]` | Tareas afectadas |
| `result.failures[].spec_amendment` | `dict` | Enmienda sugerida: `target_file`, `section`, `action`, `content` |
| `agent_format` | `str` | Formato del agente (`claude-code`, `cursor`, etc.) |

### gitlab_ci.yml.j2 / github_actions.yml.j2

| Variable | Tipo | Descripcion |
|----------|------|-------------|
| `spec_dir` | `str` | Path al directorio de la spec |

---

## Sintaxis Jinja2

Los templates usan [Jinja2](https://jinja.palletsprojects.com/) con estas opciones habilitadas:

- **`trim_blocks`**: el primer newline despues de un bloque `{% %}` se elimina
- **`lstrip_blocks`**: whitespace al inicio de linea antes de `{% %}` se elimina
- **`keep_trailing_newline`**: se preserva el newline final del archivo

### Referencia rapida

```jinja2
{# Comentario #}

{# Variable #}
{{ variable }}

{# Loop #}
{% for item in items %}
{{ item.name }}
{% endfor %}

{# Condicional #}
{% if condition %}
contenido
{% endif %}

{# Filtro: valor por defecto #}
{{ variable | default("fallback") }}

{# Filtro: join de lista #}
{{ items | join(", ") }}

{# Filtro: longitud #}
{{ items | length }}

{# Filtro: lowercase #}
{{ text | lower }}
```

---

## Ejemplos

### Personalizar el formato de requisitos

Para agregar un campo "Owner" a cada requisito:

```bash
mkdir -p .intake/templates
```

Crear `.intake/templates/requirements.md.j2`:

```jinja2
# Requisitos del Proyecto

{% for req in functional_requirements %}
## {{ req.id }}: {{ req.title }}

{{ req.description }}

| Campo | Valor |
|-------|-------|
| Prioridad | {{ req.priority }} |
| Fuente | {{ req.source }} |
| Owner | _(por asignar)_ |

**Criterios de aceptacion:**
{% for ac in req.acceptance_criteria %}
- [ ] {{ ac }}
{% endfor %}

{% endfor %}
```

### Personalizar verify.sh para un entorno especifico

Para agregar setup de entorno antes de los checks:

Crear `.intake/templates/verify_sh.j2`:

```jinja2
#!/usr/bin/env bash
# Verification script — {{ spec_name }}
set -euo pipefail

PROJECT_DIR="${1:-.}"
PASSED=0
FAILED=0
TOTAL=0

# Setup del entorno (personalizado)
source "${PROJECT_DIR}/.env.test" 2>/dev/null || true
export DATABASE_URL="${DATABASE_URL:-sqlite:///test.db}"

check() {
    local name="$1"
    local cmd="$2"
    TOTAL=$((TOTAL + 1))
    echo -n "  [$TOTAL] $name ... "
    if (cd "$PROJECT_DIR" && eval "$cmd") > /dev/null 2>&1; then
        echo "PASS"
        PASSED=$((PASSED + 1))
    else
        echo "FAIL"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== Verification: {{ spec_name }} ==="
echo ""

{% for check in checks %}
check '{{ check.name }}' '{{ check.command }}'
{% endfor %}

echo ""
echo "=== Results: $PASSED passed, $FAILED failed (of $TOTAL) ==="

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
exit 0
```

### Personalizar la configuracion CI generada

Para agregar cache y notificaciones a GitHub Actions:

Crear `.intake/templates/github_actions.yml.j2`:

```jinja2
name: intake-verify

on:
  pull_request:
  push:
    branches: [main, develop]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: {% raw %}${{ runner.os }}{% endraw %}-pip-intake
      - run: pip install intake-ai-cli --quiet
      - run: intake validate {{ spec_dir }} --strict
      - run: intake verify {{ spec_dir }} -p . --format junit -o report.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: intake-report
          path: report.xml
```

### Agregar branding corporativo a las specs

Para que todas las specs tengan un header corporativo, sobreescribe `context.md.j2`:

```jinja2
# Project Context

> Generated by intake for ACME Corp. Confidential.

| Field | Value |
|-------|-------|
| Project | {{ project_name }} |
| Language | {{ language }} |
{% if stack %}
| Stack | {{ stack | join(", ") }} |
{% endif %}
| Classification | Internal Use Only |

{% if conventions %}
## Conventions

{% for key, value in conventions.items() %}
- **{{ key }}:** {{ value }}
{% endfor %}
{% endif %}

## Metrics

| Category | Count |
|----------|-------|
| Functional requirements | {{ functional_count }} |
| Non-functional requirements | {{ non_functional_count }} |
| Open questions | {{ question_count }} |
| Risks | {{ risk_count }} |
| Tasks | {{ task_count }} |
| Checks | {{ check_count }} |

{% if risks %}
## Key Risks

{% for risk in risks %}
- **{{ risk.id }}** [{{ risk.category }}] P={{ risk.probability }} I={{ risk.impact }}: {{ risk.description }}
{% endfor %}
{% endif %}
```

---

## Listar templates activos

El `TemplateLoader` puede listar todos los templates disponibles y su origen:

```python
from intake.templates.loader import TemplateLoader

loader = TemplateLoader(project_dir=".")
for name, source in loader.list_templates().items():
    print(f"  {name}: {source}")
```

Posibles valores de `source`:

| Valor | Significado |
|-------|-------------|
| `builtin` | Template incluido en intake |
| `user` | Template de usuario (no sobreescribe un built-in) |
| `user (override)` | Template de usuario que sobreescribe un built-in |

---

## Buenas practicas

1. **Empezar desde el built-in.** Copia el template original de `src/intake/templates/` antes de modificarlo. Asi no pierdes variables ni estructura.

2. **Probar los cambios.** Despues de crear un override, ejecuta `intake init` o `intake export` y revisa el output.

3. **Versionar los templates.** Commitea `.intake/templates/` en git para que todo el equipo use los mismos templates.

4. **Mantener compatibilidad.** Si actualizas intake, revisa si los templates built-in cambiaron y actualiza tus overrides si es necesario.

5. **Usar `warn_on_override: true`.** El log te avisa cuando un template built-in esta siendo sobreescrito, util para detectar overrides olvidados.

6. **No sobreescribir todo.** Solo sobreescribe los templates que necesitas cambiar. Los demas se cargan automaticamente del built-in.
