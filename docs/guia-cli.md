# Guia CLI

intake proporciona 22 comandos y subcomandos (incluyendo subcomandos de `plugins`, `task` y `mcp`). Todos siguen el patron:

```bash
intake <comando> [argumentos] [opciones]
```

Para ver la ayuda de cualquier comando:

```bash
intake --help
intake <comando> --help
```

---

## intake init

Genera una spec completa a partir de fuentes de requisitos. Este es el comando principal.

```bash
intake init <DESCRIPCION> -s <fuente> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `DESCRIPCION` | texto | Si | Frase corta describiendo que construir. Se convierte en slug para el nombre del directorio (max 50 caracteres). |

### Opciones

| Flag | Corto | Tipo | Default | Requerido | Descripcion |
|------|-------|------|---------|-----------|-------------|
| `--source` | `-s` | texto | — | Si | Fuente de requisitos (repetible). Path a archivo, URL, o `-` para stdin. |
| `--mode` | | opcion | auto | No | Modo de generacion: `quick`, `standard`, `enterprise`. Si no se especifica, se auto-clasifica. |
| `--model` | `-m` | texto | config o `claude-sonnet-4` | No | Modelo LLM a usar para el analisis. |
| `--lang` | `-l` | texto | config o `en` | No | Idioma del contenido generado en la spec. |
| `--project-dir` | `-p` | path | `.` | No | Directorio del proyecto existente (para auto-deteccion del stack). |
| `--stack` | | texto | auto-detectado | No | Stack tecnologico. Ej: `python,fastapi,postgresql`. |
| `--output` | `-o` | path | `./specs` | No | Directorio de salida para la spec. |
| `--format` | `-f` | opcion | config o ninguno | No | Formato de exportacion: `architect`, `claude-code`, `cursor`, `kiro`, `copilot`, `generic`. |
| `--preset` | | opcion | ninguno | No | Preset de configuracion: `minimal`, `standard`, `enterprise`. |
| `--interactive` | `-i` | flag | false | No | Modo interactivo: pregunta antes de generar cada seccion. |
| `--dry-run` | | flag | false | No | Muestra que haria sin generar archivos. |
| `--verbose` | `-v` | flag | false | No | Output detallado. |

### Ejemplos

```bash
# Desde un archivo Markdown
intake init "API de usuarios" -s requirements.md

# Desde multiples fuentes
intake init "Pasarela de pagos" -s jira.json -s confluence.html -s notas.md

# Con modelo especifico y preset enterprise
intake init "Sistema critico" -s reqs.yaml --model gpt-4o --preset enterprise

# Con stack manual y formato de exportacion
intake init "Microservicio" -s reqs.md --stack python,fastapi -f architect

# Spec en espanol
intake init "Carrito de compras" -s historias.md --lang es

# Modo rapido (solo context.md + tasks.md)
intake init "Fix login bug" -s notas.txt --mode quick

# Modo enterprise (todos los archivos + riesgos detallados)
intake init "Sistema critico" -s reqs.yaml --mode enterprise

# Desde una URL
intake init "API review" -s https://wiki.company.com/rfc/auth

# Desde un export de Slack
intake init "Decisiones de sprint" -s slack_export.json

# Desde GitHub Issues
intake init "Bug fixes" -s issues.json

# Desde conectores API directos (requiere config en .intake.yaml)
intake init "Sprint tasks" -s jira://PROJ-123
intake init "Spec review" -s confluence://SPACE/Page-Title
intake init "Bug triage" -s github://org/repo/issues?labels=bug&state=open
intake init "Sprint review" -s gitlab://team/backend/issues?labels=sprint

# Dry run para ver que haria
intake init "Prototipo" -s ideas.txt --dry-run

# Desde stdin
cat requisitos.txt | intake init "Feature X" -s -
```

### Que hace internamente

1. Carga la configuracion (preset + `.intake.yaml` + flags CLI)
2. Auto-detecta el stack tecnologico del proyecto (si no se especifica `--stack`)
3. Slugifica la descripcion para el nombre del directorio
4. **Resolucion de fuentes**: cada fuente se resuelve via `parse_source()`:
   - Archivos locales → se parsean con el registry
   - URLs (`http://`, `https://`) → se procesan con `UrlParser`
   - URIs de esquema (`jira://`, `confluence://`, `github://`, `gitlab://`) → se resuelven via conectores API (ver [Conectores](conectores.md))
   - Stdin (`-`) → se lee como texto plano
   - Texto libre → se trata como plaintext
5. **Clasificacion de complejidad**: si no se especifica `--mode`, se auto-clasifica:
   - `quick`: <500 palabras, 1 fuente, sin estructura
   - `standard`: caso por defecto
   - `enterprise`: 4+ fuentes O >5000 palabras
6. **Fase 1 — Ingest**: parsea todas las fuentes via el registry
7. **Fase 2 — Analyze**: extraccion LLM, deduplicacion, validacion, riesgos, diseno
8. **Fase 3 — Generate**: renderiza archivos segun el modo (quick: 2, standard/enterprise: 6) + `spec.lock.yaml`
9. **Fase 5 — Export**: exporta al formato elegido (si se especifico `--format`)

---

## intake add

Agrega fuentes a una spec existente.

```bash
intake add <SPEC_DIR> -s <fuente> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec existente. |

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--source` | `-s` | texto | — | Nuevas fuentes a agregar (repetible). |
| `--regenerate` | | flag | false | Regenerar toda la spec incluyendo las nuevas fuentes. |
| `--verbose` | `-v` | flag | false | Output detallado. |

### Ejemplo

```bash
# Agregar una fuente nueva a una spec existente
intake add specs/api-de-usuarios/ -s feedback-qa.md

# Agregar y regenerar todo
intake add specs/api-de-usuarios/ -s nuevos-reqs.yaml --regenerate
```

---

## intake regenerate

Regenera una spec desde cero con nuevas fuentes. Equivalente a `intake add SPEC_DIR --regenerate -s SOURCES`.

```bash
intake regenerate <SPEC_DIR> -s <fuente> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec existente. |

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--source` | `-s` | texto | — | Fuentes para regenerar (repetible). Requerido. |
| `--verbose` | `-v` | flag | false | Output detallado. |

### Ejemplo

```bash
# Regenerar spec con fuentes actualizadas
intake regenerate specs/api-de-usuarios/ -s requirements-v2.md -s notas.md

# Regenerar con verbose
intake regenerate specs/api-de-usuarios/ -s reqs.md -v
```

---

## intake verify

Verifica que la implementacion cumple con la spec ejecutando los checks de `acceptance.yaml`.

```bash
intake verify <SPEC_DIR> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec. |

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--project-dir` | `-p` | path | `.` | Directorio del proyecto a verificar. |
| `--format` | `-f` | opcion | `terminal` | Formato del reporte: `terminal`, `json`, `junit`. |
| `--tags` | `-t` | texto | todos | Solo ejecutar checks con estos tags (repetible). |
| `--fail-fast` | | flag | false | Detenerse en el primer check requerido que falle. |

### Exit codes

| Codigo | Significado |
|--------|-------------|
| `0` | Todos los checks requeridos pasaron |
| `1` | Al menos un check requerido fallo |
| `2` | Error de ejecucion (spec no encontrada, YAML invalido, etc.) |

### Ejemplos

```bash
# Verificar con reporte en terminal
intake verify specs/api-de-usuarios/ -p .

# Solo checks con tag "api"
intake verify specs/api-de-usuarios/ -p . -t api

# Formato JUnit para CI
intake verify specs/api-de-usuarios/ -p . -f junit > test-results.xml

# Fail fast
intake verify specs/api-de-usuarios/ -p . --fail-fast

# Formato JSON
intake verify specs/api-de-usuarios/ -p . -f json
```

---

## intake export

Exporta una spec a un formato listo para un agente IA.

```bash
intake export <SPEC_DIR> -f <formato> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec. |

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--format` | `-f` | opcion | — | Formato: `architect`, `claude-code`, `cursor`, `kiro`, `copilot`, `generic`. Requerido. |
| `--output` | `-o` | path | `.` | Directorio de salida. |

### Ejemplos

```bash
# Exportar para architect
intake export specs/api-de-usuarios/ -f architect -o output/

# Exportar formato generico
intake export specs/api-de-usuarios/ -f generic -o output/

# Exportar para Claude Code (genera CLAUDE.md + .intake/)
intake export specs/api-de-usuarios/ -f claude-code -o .

# Exportar para Cursor (genera .cursor/rules/)
intake export specs/api-de-usuarios/ -f cursor -o .

# Exportar para Kiro (formato nativo con checkboxes)
intake export specs/api-de-usuarios/ -f kiro -o .

# Exportar para GitHub Copilot (genera .github/copilot-instructions.md)
intake export specs/api-de-usuarios/ -f copilot -o .
```

---

## intake show

Muestra un resumen de una spec: requisitos, tareas, checks, costos.

```bash
intake show <SPEC_DIR>
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec. |

### Que muestra

- Archivos en la spec
- Modelo LLM usado
- Cantidad de requisitos
- Cantidad de tareas
- Costo total del analisis
- Fecha de creacion
- Cantidad de fuentes
- Cantidad de checks de aceptacion

### Ejemplo

```bash
intake show specs/api-de-usuarios/
```

---

## intake list

Lista todas las specs en un directorio.

```bash
intake list [opciones]
```

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--dir` | `-d` | path | `./specs` | Directorio donde buscar specs. |

Busca recursivamente subdirectorios que contengan `requirements.md` o `acceptance.yaml`. Soporta specs anidadas en cualquier profundidad.

### Ejemplo

```bash
# Listar specs en el directorio por defecto
intake list

# Listar specs en otro directorio
intake list -d ./mi-proyecto/specs
```

---

## intake diff

Compara dos versiones de una spec y muestra los cambios.

```bash
intake diff <SPEC_A> <SPEC_B> [opciones]
```

### Argumentos

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_A` | path | Si | Primera version de la spec. |
| `SPEC_B` | path | Si | Segunda version de la spec. |

### Opciones

| Flag | Tipo | Default | Descripcion |
|------|------|---------|-------------|
| `--section` | opcion | `all` | Que seccion comparar: `requirements`, `design`, `tasks`, `acceptance`, `all`. |

### Que compara

- **requirements**: Requisitos por ID (FR-XX, NFR-XX)
- **tasks**: Tareas por numero
- **acceptance**: Checks por ID

Los cambios se muestran como:
- **Added** (verde): elementos nuevos en SPEC_B
- **Removed** (rojo): elementos que estaban en SPEC_A pero no en SPEC_B
- **Modified** (amarillo): elementos con cambios

### Ejemplo

```bash
# Comparar dos versiones completas
intake diff specs/v1/ specs/v2/

# Solo comparar requisitos
intake diff specs/v1/ specs/v2/ --section requirements
```

---

## intake doctor

Diagnostica el entorno y la configuracion.

```bash
intake doctor [opciones]
```

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--fix` | | flag | false | Intentar corregir los problemas detectados automaticamente. |
| `--verbose` | `-v` | flag | false | Output detallado. |

### Checks que ejecuta

| Check | Que verifica | Auto-fixable |
|-------|-------------|--------------|
| Python version | Python >= 3.12 | No |
| LLM API key | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, o `llm.api_key_env` de `.intake.yaml` | No |
| pdfplumber | Paquete instalado | Si |
| python-docx | Paquete instalado | Si |
| beautifulsoup4 | Paquete instalado | Si |
| markdownify | Paquete instalado | Si |
| litellm | Paquete instalado | Si |
| jinja2 | Paquete instalado | Si |
| Config file | `.intake.yaml` existe, es YAML valido, y pasa validacion de esquema Pydantic | Si (crea uno basico) |
| Connectors | Credenciales de Jira, Confluence, GitHub, GitLab (si estan configurados) | No |

### --fix

Con `--fix`, intake intenta corregir automaticamente:

- **Paquetes faltantes**: ejecuta `pip install <paquete>` (detecta `pip3.12`, `pip3` o `pip`)
- **Config faltante**: crea un `.intake.yaml` basico con defaults

### Ejemplos

```bash
# Solo diagnosticar
intake doctor

# Diagnosticar y corregir
intake doctor --fix

# Con output detallado
intake doctor -v
```

---

## intake plugins list

Lista todos los plugins descubiertos (parsers, exporters, connectors).

```bash
intake plugins list [opciones]
```

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--verbose` | `-v` | flag | false | Mostrar columnas adicionales: modulo y errores de carga. |

### Que muestra

Una tabla con:

| Columna | Descripcion |
|---------|-------------|
| Name | Nombre del plugin |
| Group | Grupo: parsers, exporters, connectors |
| Version | Version del paquete que lo provee |
| V2 | Si implementa el protocolo V2 |
| Built-in | Si es un plugin built-in de intake |

Con `-v` se agregan columnas de modulo y errores de carga.

### Ejemplo

```bash
# Lista basica
intake plugins list

# Con detalles
intake plugins list -v
```

---

## intake plugins check

Valida la compatibilidad de todos los plugins descubiertos.

```bash
intake plugins check
```

Ejecuta `check_compatibility()` en cada plugin y reporta OK o FAIL con detalles del error.

---

## intake task list

Lista las tareas de una spec con su estado actual.

```bash
intake task list <SPEC_DIR> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec. |

### Opciones

| Flag | Tipo | Default | Descripcion |
|------|------|---------|-------------|
| `--status` | opcion | todos | Filtrar por estado (repetible): `pending`, `in_progress`, `done`, `blocked`. |

### Que muestra

- Tabla con ID, titulo y estado de cada tarea
- Resumen de progreso: total, pending, in_progress, done, blocked

### Ejemplo

```bash
# Listar todas las tareas
intake task list specs/mi-feature/

# Solo tareas pendientes y en progreso
intake task list specs/mi-feature/ --status pending --status in_progress
```

---

## intake task update

Actualiza el estado de una tarea en `tasks.md`.

```bash
intake task update <SPEC_DIR> <TASK_ID> <STATUS> [opciones]
```

### Argumentos

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec. |
| `TASK_ID` | entero | Si | ID de la tarea a actualizar. |
| `STATUS` | opcion | Si | Nuevo estado: `pending`, `in_progress`, `done`, `blocked`. |

### Opciones

| Flag | Tipo | Default | Descripcion |
|------|------|---------|-------------|
| `--note` | texto | ninguno | Nota o anotacion para agregar a la actualizacion. |

### Ejemplo

```bash
# Marcar tarea 1 como completada
intake task update specs/mi-feature/ 1 done

# Marcar como en progreso con nota
intake task update specs/mi-feature/ 2 in_progress --note "Iniciando implementacion"

# Marcar como bloqueada
intake task update specs/mi-feature/ 3 blocked --note "Esperando API de terceros"
```

---

## intake feedback

Analiza fallos de verificacion y sugiere correcciones a la spec o la implementacion.

```bash
intake feedback <SPEC_DIR> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec. |

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--verify-report` | `-r` | path | ninguno | Archivo JSON con reporte de verificacion. Si no se proporciona, ejecuta `verify` primero. |
| `--project-dir` | `-p` | path | `.` | Directorio del proyecto. |
| `--apply` | | flag | false | Aplicar enmiendas sugeridas directamente a la spec. |
| `--agent-format` | | opcion | `generic` | Formato de sugerencias: `generic`, `claude-code`, `cursor`. |
| `--verbose` | `-v` | flag | false | Output detallado. |

### Que hace

1. **Carga el reporte de verificacion**: si no se proporciona `--verify-report`, ejecuta `intake verify` primero para obtener uno
2. **Analisis LLM**: envia los checks fallidos junto con la spec al LLM para analisis de causa raiz
3. **Genera sugerencias**: para cada fallo, produce:
   - Causa raiz
   - Sugerencia de correccion
   - Severidad (critical, major, minor)
   - Tareas afectadas
   - Enmienda propuesta a la spec (opcional)
4. **Aplica enmiendas** (si `--apply` o `feedback.auto_amend_spec` en config): modifica la spec directamente

### Ejemplos

```bash
# Analizar fallos con reporte existente
intake feedback specs/mi-feature/ --verify-report report.json

# Ejecutar verify + analizar todo en un paso
intake feedback specs/mi-feature/ -p .

# Aplicar enmiendas automaticamente
intake feedback specs/mi-feature/ -p . --apply

# Sugerencias en formato para Claude Code
intake feedback specs/mi-feature/ -p . --agent-format claude-code
```

### Exit codes

| Codigo | Significado |
|--------|-------------|
| `0` | Analisis completado (con o sin sugerencias) |
| `2` | Error de ejecucion |

---

## intake mcp serve

Inicia el servidor MCP (Model Context Protocol) para integracion con agentes IA.

```bash
intake mcp serve [opciones]
```

### Opciones

| Flag | Tipo | Default | Descripcion |
|------|------|---------|-------------|
| `--transport` | opcion | `stdio` | Transporte: `stdio` (para agentes CLI) o `sse` (HTTP para IDEs). |
| `--port` | entero | `8080` | Puerto para transporte SSE. |
| `--specs-dir` | path | `./specs` | Directorio base donde viven las specs. |
| `--project-dir` | path | `.` | Directorio del proyecto para verificacion. |

### Que expone

**9 Tools:**

| Tool | Descripcion |
|------|-------------|
| `intake_show` | Muestra resumen del spec con contenido de archivos |
| `intake_get_context` | Lee context.md del spec |
| `intake_get_tasks` | Lista tareas con filtro por status (all/pending/in_progress/done/blocked) |
| `intake_update_task` | Actualiza el status de una tarea con nota opcional |
| `intake_verify` | Ejecuta checks de aceptacion con filtro por tags |
| `intake_feedback` | Verifica + genera feedback sobre fallos |
| `intake_list_specs` | Lista specs disponibles |
| `intake_validate` | Valida consistencia interna de la spec (cross-references, DAG, checks) |
| `intake_estimate` | Estima costo LLM para generar o regenerar una spec |

**6 Resources** via URIs `intake://specs/{name}/{section}`:
- `requirements`, `tasks`, `context`, `acceptance`, `design`, `sources`

**2 Prompts:**
- `implement_next_task`: contexto del spec + siguiente tarea pendiente + instrucciones
- `verify_and_fix`: loop de verificar -> arreglar -> re-verificar

### Ejemplos

```bash
# Iniciar con transporte stdio (para Claude Code, etc.)
intake mcp serve --transport stdio

# Iniciar con transporte SSE (HTTP)
intake mcp serve --transport sse --port 8080

# Con directorio de specs personalizado
intake mcp serve --specs-dir ./my-specs --project-dir /path/to/project
```

### Requisitos

Requiere el paquete `mcp`: `pip install intake-ai-cli[mcp]`

---

## intake watch

Monitorea archivos del proyecto y re-ejecuta verificacion automaticamente ante cambios.

```bash
intake watch <SPEC_DIR> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec con `acceptance.yaml`. |

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--project-dir` | `-p` | path | `.` | Directorio del proyecto a monitorear. |
| `--tags` | `-t` | texto | todos | Solo ejecutar checks con estos tags (repetible). |
| `--debounce` | | float | `2.0` | Segundos de espera antes de re-ejecutar (debouncing). |
| `--verbose` | `-v` | flag | false | Output detallado con archivos cambiados. |

### Que hace

1. Carga `acceptance.yaml` del directorio de spec
2. Ejecuta una verificacion inicial (equivalente a `run_once()`)
3. Monitorea el directorio del proyecto usando `watchfiles` (Rust-based, eficiente)
4. Cuando detecta cambios en archivos:
   - Filtra archivos ignorados (*.pyc, __pycache__, .git, node_modules, .intake)
   - Espera el tiempo de debounce configurado
   - Re-ejecuta los checks de aceptacion
   - Muestra resultados en terminal con Rich

### Patrones ignorados por defecto

- `*.pyc`
- `__pycache__`
- `.git`
- `node_modules`
- `.intake`

Personalizables via `watch.ignore_patterns` en `.intake.yaml`.

### Ejemplos

```bash
# Watch basico
intake watch specs/mi-feature/ -p .

# Con filtro de tags y verbose
intake watch specs/mi-feature/ -p . -t tests -t lint --verbose

# Con debounce personalizado
intake watch specs/mi-feature/ -p . --debounce 5

# Solo checks de seguridad
intake watch specs/mi-feature/ -p . -t security
```

### Requisitos

Requiere el paquete `watchfiles`: `pip install intake-ai-cli[watch]`

---

## intake validate

Valida la consistencia interna de una spec (quality gate). Comprueba cross-references, dependencias de tareas, validez de checks de aceptacion y completeness. Funciona offline — no requiere LLM.

```bash
intake validate <SPEC_DIR> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec a validar. |

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--strict` | | flag | false | Modo estricto: los warnings se convierten en errores. |
| `--format` | `-f` | opcion | `terminal` | Formato del reporte: `terminal`, `json`. |

### Categorias de checks

| Categoria | Que verifica |
|-----------|-------------|
| `structure` | Archivos requeridos existen y no estan vacios; YAML es valido |
| `cross_reference` | Tareas y checks de aceptacion referencian requisitos validos; requisitos no estan huerfanos |
| `consistency` | DAG de tareas sin ciclos; IDs de tareas son secuenciales |
| `acceptance` | Checks tienen tipo valido, comandos no vacios, patrones regex validos, paths definidos |
| `completeness` | Cada requisito funcional tiene al menos una tarea implementadora |

### Exit codes

| Codigo | Significado |
|--------|-------------|
| `0` | Spec es valida (sin errores) |
| `1` | Spec tiene errores |
| `2` | Error de ejecucion |

### Ejemplos

```bash
# Validar spec (reporte en terminal)
intake validate specs/api-de-usuarios/

# Modo estricto: warnings se convierten en errores
intake validate specs/api-de-usuarios/ --strict

# Formato JSON (para CI o procesamiento automatizado)
intake validate specs/api-de-usuarios/ --format json

# Usar antes de entregar a un agente
intake validate specs/mi-feature/ && intake export specs/mi-feature/ -f claude-code -o .
```

---

## intake estimate

Estima el costo LLM antes de generar una spec. Analiza las fuentes de entrada y calcula el uso de tokens y costo en dolares sin hacer ninguna llamada LLM.

```bash
intake estimate -s <fuente> [opciones]
```

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--source` | `-s` | texto | — | Fuentes a estimar (repetible). Requerido. |
| `--model` | `-m` | texto | config | Modelo LLM para calcular precio. |
| `--mode` | | opcion | auto | Modo: `quick`, `standard`, `enterprise`. Auto-detectado si se omite. |
| `--format` | `-f` | opcion | `terminal` | Formato del reporte: `terminal`, `json`. |

### Que muestra

- Modelo LLM usado
- Modo de generacion (con indicador de auto-deteccion)
- Palabras de entrada estimadas
- Tokens de entrada y salida estimados
- Numero de llamadas LLM
- Costo estimado con margen de ~30%
- Warnings: modelo no en tabla de precios, presupuesto excedido

### Modelos con precios integrados

| Modelo | Input ($/1M tokens) | Output ($/1M tokens) |
|--------|---------------------|----------------------|
| `claude-sonnet-4` | $3.00 | $15.00 |
| `claude-opus-4` | $15.00 | $75.00 |
| `claude-haiku-4` | $0.80 | $4.00 |
| `gpt-4o` | $2.50 | $10.00 |
| `gpt-4o-mini` | $0.15 | $0.60 |
| `gemini-2.0-flash` | $0.10 | $0.40 |
| `deepseek-chat` | $0.14 | $0.28 |

Para modelos no listados se usa un pricing por defecto ($3/$15 per 1M tokens) con un warning.

### Ejemplos

```bash
# Estimar costo de un archivo
intake estimate -s requirements.md

# Multiples fuentes con modelo especifico
intake estimate -s reqs.md -s notes.md --model gpt-4o-mini

# Forzar modo enterprise
intake estimate -s big-spec.pdf --mode enterprise

# Formato JSON
intake estimate -s reqs.md --format json
```

---

## intake export-ci

Genera configuracion de CI para verificacion automatica de specs.

```bash
intake export-ci <SPEC_DIR> -p <plataforma> [opciones]
```

### Argumento

| Argumento | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| `SPEC_DIR` | path | Si | Directorio de la spec. |

### Opciones

| Flag | Corto | Tipo | Default | Descripcion |
|------|-------|------|---------|-------------|
| `--platform` | `-p` | opcion | — | Plataforma CI: `github`, `gitlab`. Requerido. |
| `--output` | `-o` | path | `.` | Directorio de salida. |

### Que genera

| Plataforma | Archivo generado | Descripcion |
|-----------|-----------------|-------------|
| `github` | `.github/workflows/intake-verify.yml` | GitHub Actions workflow |
| `gitlab` | `.gitlab-ci.yml` | GitLab CI pipeline |

Los archivos generados son templates Jinja2 renderizados con el path de la spec. Incluyen instalacion de intake, ejecucion de `intake verify`, y reporte JUnit.

### Ejemplos

```bash
# Generar GitLab CI config
intake export-ci specs/auth/ -p gitlab

# Generar GitHub Actions workflow en directorio personalizado
intake export-ci specs/auth/ -p github -o .github/workflows/

# Generar y commitear
intake export-ci specs/mi-feature/ -p gitlab && git add .gitlab-ci.yml
```

---

## Opciones globales

| Flag | Descripcion |
|------|-------------|
| `--version` | Muestra la version de intake |
| `--help` | Muestra la ayuda del comando |

```bash
intake --version    # intake, version 1.0.0
intake --help       # Ayuda general
intake init --help  # Ayuda del comando init
```

---

## Exit codes

Todos los comandos siguen un esquema de exit codes consistente:

| Codigo | Significado |
|--------|-------------|
| `0` | Exito |
| `1` | Check requerido fallo (solo `verify`) |
| `2` | Error de ejecucion |
