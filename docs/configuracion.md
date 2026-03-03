# Configuracion

intake funciona sin configuracion — solo necesita una API key de LLM. Para personalizar el comportamiento, se usa un archivo `.intake.yaml` en la raiz del proyecto.

---

## Prioridad de carga

La configuracion se carga por capas. Cada capa sobreescribe la anterior:

```
CLI flags  >  .intake.yaml  >  preset  >  defaults
```

1. **Defaults**: valores por defecto en el codigo
2. **Preset**: si se usa `--preset`, aplica un conjunto predefinido
3. **`.intake.yaml`**: archivo de configuracion del proyecto
4. **CLI flags**: las opciones de linea de comandos siempre ganan

---

## Archivo .intake.yaml

Crea un archivo `.intake.yaml` en la raiz de tu proyecto. Ejemplo completo:

```yaml
# Configuracion del modelo LLM
llm:
  model: claude-sonnet-4         # Cualquier modelo soportado por LiteLLM
  api_key_env: ANTHROPIC_API_KEY  # Variable de entorno con la API key
  max_cost_per_spec: 0.50         # Presupuesto maximo por spec (USD)
  temperature: 0.2                # 0.0 = determinista, 1.0 = creativo
  max_retries: 3                  # Reintentos en caso de fallo
  timeout: 120                    # Timeout por llamada LLM (segundos)

# Configuracion del proyecto
project:
  name: mi-proyecto               # Nombre (auto-detectado si vacio)
  stack: []                       # Stack tecnologico (auto-detectado si vacio)
  language: en                    # Idioma del contenido generado
  conventions: {}                 # Convenciones personalizadas (key: value)

# Configuracion de la spec
spec:
  output_dir: ./specs             # Donde guardar las specs generadas
  requirements_format: ears       # ears | user-stories | bdd | free
  design_depth: moderate          # minimal | moderate | detailed
  task_granularity: medium        # coarse | medium | fine
  include_sources: true           # Incluir trazabilidad de fuentes
  version_specs: true             # Crear directorios versionados
  generate_lock: true             # Generar spec.lock.yaml
  risk_assessment: true           # Incluir evaluacion de riesgos
  auto_mode: true                 # Auto-detectar quick/standard/enterprise

# Configuracion de verificacion
verification:
  auto_generate_tests: true       # Generar checks de aceptacion
  test_output_dir: ./tests/generated
  checks: []                      # Checks personalizados adicionales
  timeout_per_check: 120          # Timeout por check (segundos)

# Configuracion de exportacion
export:
  default_format: generic         # architect | claude-code | cursor | kiro | generic
  architect_include_guardrails: true
  architect_pipeline_template: standard
  claude_code_generate_claude_md: true

# Conectores (preparacion para Fase 2)
connectors:
  jira:
    url: ""                       # URL base de Jira
    email: ""                     # Email de autenticacion
    api_token_env: JIRA_API_TOKEN # Variable de entorno con el API token
  confluence:
    url: ""                       # URL base de Confluence
    email: ""                     # Email de autenticacion
    api_token_env: CONFLUENCE_API_TOKEN  # Variable de entorno con el API token
  github:
    token_env: GITHUB_TOKEN       # Variable de entorno con el token

# Seguridad
security:
  redact_patterns: []             # Patrones regex a redactar del output
  redact_files:                   # Archivos a nunca incluir
    - "*.env"
    - "*.pem"
    - "*.key"
```

---

## Referencia completa de campos

### Seccion `llm`

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `model` | string | `claude-sonnet-4` | Modelo LLM. Cualquier modelo que [LiteLLM](https://docs.litellm.ai/docs/providers) soporte. |
| `api_key_env` | string | `ANTHROPIC_API_KEY` | Nombre de la variable de entorno que contiene la API key. |
| `max_cost_per_spec` | float | `0.50` | Presupuesto maximo por spec en USD. Si se excede, el analisis se detiene. |
| `temperature` | float | `0.2` | Temperatura del modelo. Menor = mas determinista. |
| `max_retries` | int | `3` | Numero de reintentos ante fallos del LLM. |
| `timeout` | int | `120` | Timeout por llamada LLM en segundos. |

**Modelos soportados:**

| Proveedor | Ejemplos | Variable de entorno |
|-----------|----------|---------------------|
| Anthropic | `claude-sonnet-4`, `claude-opus-4`, `claude-haiku-4-5` | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-4o`, `gpt-4`, `gpt-3.5-turbo` | `OPENAI_API_KEY` |
| Google | `gemini/gemini-pro`, `gemini/gemini-flash` | `GEMINI_API_KEY` |
| Local | `ollama/llama3`, `ollama/mistral` | (no necesita key) |

### Seccion `project`

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `name` | string | `""` | Nombre del proyecto. Si esta vacio, se genera desde la descripcion del `init`. |
| `stack` | list[string] | `[]` | Stack tecnologico. Si esta vacio, se auto-detecta desde archivos del proyecto. |
| `language` | string | `en` | Idioma para el contenido generado (ej: `en`, `es`, `fr`). |
| `conventions` | dict | `{}` | Convenciones del proyecto como pares clave-valor. |

La auto-deteccion del stack busca 28+ archivos marcadores en el directorio del proyecto:

| Archivo | Stack detectado |
|---------|----------------|
| `package.json` | javascript, node |
| `tsconfig.json` | typescript |
| `pyproject.toml` | python |
| `Cargo.toml` | rust |
| `go.mod` | go |
| `pom.xml` | java, maven |
| `Dockerfile` | docker |
| `next.config.js` | nextjs |
| ... | ... |

Ademas inspecciona el contenido de `pyproject.toml` y `package.json` para detectar frameworks (fastapi, django, react, vue, etc.).

### Seccion `spec`

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `output_dir` | string | `./specs` | Directorio de salida para las specs. |
| `requirements_format` | string | `ears` | Formato de requisitos. Opciones: `ears`, `user-stories`, `bdd`, `free`. |
| `design_depth` | string | `moderate` | Nivel de detalle del diseno. Opciones: `minimal`, `moderate`, `detailed`. |
| `task_granularity` | string | `medium` | Granularidad de las tareas. Opciones: `coarse`, `medium`, `fine`. |
| `include_sources` | bool | `true` | Incluir `sources.md` con trazabilidad requisito-fuente. |
| `version_specs` | bool | `true` | Crear subdirectorios versionados para las specs. |
| `generate_lock` | bool | `true` | Generar `spec.lock.yaml` con hashes y metadata. |
| `risk_assessment` | bool | `true` | Ejecutar evaluacion de riesgos (fase adicional del LLM). |
| `auto_mode` | bool | `true` | Auto-detectar modo de generacion (quick/standard/enterprise) basado en la complejidad de las fuentes. Se ignora si se usa `--mode` en la CLI. |

**Modos de generacion:**

| Modo | Criterios de auto-deteccion | Archivos generados |
|------|---------------------------|-------------------|
| `quick` | <500 palabras, 1 fuente, sin estructura | `context.md` + `tasks.md` |
| `standard` | Todo lo que no es quick ni enterprise | Los 6 archivos spec completos |
| `enterprise` | 4+ fuentes O >5000 palabras | Los 6 archivos + riesgos detallados |

**Formatos de requisitos:**

| Formato | Descripcion | Mejor para |
|---------|-------------|-----------|
| `ears` | Easy Approach to Requirements Syntax. Formato estructurado con condiciones. | Especificaciones formales |
| `user-stories` | "Como [rol], quiero [accion] para [beneficio]". | Equipos agiles |
| `bdd` | Given/When/Then. Behavior-driven development. | Tests de aceptacion |
| `free` | Formato libre. Sin estructura impuesta. | Prototipos rapidos |

**Niveles de diseno:**

| Nivel | Descripcion |
|-------|-------------|
| `minimal` | Solo componentes principales y decisiones criticas. |
| `moderate` | Componentes, archivos, decisiones tecnicas y dependencias. |
| `detailed` | Todo lo anterior mas diagramas de interaccion, edge cases, consideraciones de performance. |

**Granularidad de tareas:**

| Nivel | Descripcion |
|-------|-------------|
| `coarse` | Tareas grandes, pocas. Cada tarea cubre un componente completo. |
| `medium` | Balance entre granularidad y cantidad. |
| `fine` | Tareas pequenas y atomicas. Cada tarea es ~15-30 minutos de trabajo. |

### Seccion `verification`

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `auto_generate_tests` | bool | `true` | Generar checks de aceptacion automaticamente desde los requisitos. |
| `test_output_dir` | string | `./tests/generated` | Directorio para tests generados. |
| `checks` | list[string] | `[]` | Checks personalizados adicionales. |
| `timeout_per_check` | int | `120` | Timeout maximo por check individual en segundos. |

### Seccion `export`

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `default_format` | string | `generic` | Formato de exportacion por defecto. Opciones: `architect`, `claude-code`, `cursor`, `kiro`, `generic`. |
| `architect_include_guardrails` | bool | `true` | Incluir guardrails en pipelines de architect. |
| `architect_pipeline_template` | string | `standard` | Template de pipeline para architect. |
| `claude_code_generate_claude_md` | bool | `true` | Generar CLAUDE.md al exportar para Claude Code. |

### Seccion `connectors` (preparacion)

Configuracion para conectores API directos. Los conectores aun no estan implementados (llegaran en una version futura), pero la infraestructura de configuracion ya esta lista.

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `jira.url` | string | `""` | URL base de la instancia Jira. |
| `jira.email` | string | `""` | Email para autenticacion Jira. |
| `jira.api_token_env` | string | `"JIRA_API_TOKEN"` | Variable de entorno con el API token de Jira. |
| `confluence.url` | string | `""` | URL base de la instancia Confluence. |
| `confluence.email` | string | `""` | Email para autenticacion Confluence. |
| `confluence.api_token_env` | string | `"CONFLUENCE_API_TOKEN"` | Variable de entorno con el API token de Confluence. |
| `github.token_env` | string | `"GITHUB_TOKEN"` | Variable de entorno con el token de GitHub. |

**Nota:** Actualmente, al usar URIs como `jira://PROJ-123` en `-s`, intake muestra un warning indicando que el conector no esta disponible. Mientras tanto, exporta los datos desde la interfaz web y usa archivos JSON.

### Seccion `security`

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `redact_patterns` | list[string] | `[]` | Patrones regex que se eliminaran del contenido generado. |
| `redact_files` | list[string] | `["*.env", "*.pem", "*.key"]` | Patrones glob de archivos que nunca se incluiran. |

---

## Presets

Los presets son configuraciones predefinidas para casos de uso comunes. Se aplican con `--preset`:

```bash
intake init "Mi feature" -s reqs.md --preset minimal
```

### Comparativa

| Campo | `minimal` | `standard` | `enterprise` |
|-------|-----------|------------|--------------|
| **Caso de uso** | Prototipo rapido | Equipos normales | Regulado / critico |
| `max_cost_per_spec` | $0.10 | $0.50 | $2.00 |
| `temperature` | 0.3 | 0.2 | 0.1 |
| `requirements_format` | `free` | `ears` | `ears` |
| `design_depth` | `minimal` | `moderate` | `detailed` |
| `task_granularity` | `coarse` | `medium` | `fine` |
| `include_sources` | false | true | true |
| `risk_assessment` | false | true | true |
| `generate_lock` | false | true | true |

### Cuando usar cada preset

- **`minimal`**: Prototipado rapido, ideas exploratorias, un solo desarrollador. Costo bajo, output minimo.
- **`standard`**: La opcion por defecto. Buen balance entre detalle y costo para equipos de 2-5 personas.
- **`enterprise`**: Para equipos grandes, proyectos regulados, o cuando se necesita trazabilidad completa y evaluacion de riesgos exhaustiva.

---

## Variables de entorno

intake busca estas variables de entorno para la autenticacion con proveedores LLM:

| Variable | Proveedor | Ejemplo |
|----------|-----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic (Claude) | `sk-ant-api03-...` |
| `OPENAI_API_KEY` | OpenAI (GPT) | `sk-...` |

Configura la variable segun tu proveedor:

```bash
# Anthropic
export ANTHROPIC_API_KEY=sk-ant-api03-tu-key-aqui

# OpenAI
export OPENAI_API_KEY=sk-tu-key-aqui
```

Si usas un proveedor diferente, configura `llm.api_key_env` en `.intake.yaml`:

```yaml
llm:
  model: gemini/gemini-pro
  api_key_env: GEMINI_API_KEY
```

---

## Generar config automaticamente

Si no tienes `.intake.yaml`, intake usa defaults sensatos. Para crear un archivo de configuracion basico:

```bash
intake doctor --fix
```

Esto crea un `.intake.yaml` minimo que puedes personalizar:

```yaml
# intake configuration
llm:
  model: claude-sonnet-4
  # max_cost_per_spec: 0.50
project:
  name: ""
  language: en
  # stack: []
spec:
  output_dir: ./specs
```
