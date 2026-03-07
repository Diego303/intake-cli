# Servidor MCP

intake expone las specs como un servidor [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) para que agentes IA puedan consumir specs programaticamente. Esto permite integracion directa con agentes como Claude Code, Cursor, y cualquier cliente MCP compatible.

```bash
intake mcp serve [OPTIONS]
```

---

## Descripcion general

El servidor MCP de intake (nombre: `intake-spec`) proporciona:

- **9 herramientas (tools)** — operaciones sobre specs: consultar, verificar, validar, estimar costos, actualizar tareas, analizar fallos
- **6 recursos (resources)** — acceso directo a los archivos spec via URIs `intake://`
- **2 prompts** — plantillas estructuradas para flujos de implementacion y correccion
- **2 transportes** — stdio (local) y SSE (red)

El servidor permite que un agente IA acceda a la spec completa, consulte tareas pendientes, actualice el estado de las tareas, ejecute verificacion, y obtenga sugerencias de correccion — todo sin salir de su flujo de trabajo.

---

## Instalacion

El servidor MCP requiere dependencias opcionales:

```bash
pip install "intake-ai-cli[mcp]"
```

Esto instala el paquete `mcp` necesario para el protocolo.

Para el transporte SSE (HTTP), se necesitan dependencias adicionales:

```bash
pip install "intake-ai-cli[mcp]" starlette uvicorn
```

### Verificar instalacion

```bash
intake doctor    # verifica que el paquete mcp esta disponible
```

---

## Comando CLI

```bash
intake mcp serve [OPTIONS]
```

### Opciones

| Opcion | Default | Descripcion |
|--------|---------|-------------|
| `--specs-dir` | `./specs` | Directorio base donde residen las specs |
| `--project-dir` | `.` | Directorio del proyecto para verificacion |
| `--transport` | `stdio` | Transporte: `stdio` o `sse` |
| `--port` | `8080` | Puerto para el transporte SSE |

### Ejemplos

```bash
# stdio (default, para agentes locales como Claude Code)
intake mcp serve

# Directorio de specs personalizado
intake mcp serve --specs-dir ./output/specs

# SSE (para agentes remotos o en red)
intake mcp serve --transport sse --port 9090

# Combinacion de opciones
intake mcp serve --specs-dir ./specs --project-dir /path/to/project --transport sse --port 8080
```

---

## Herramientas (Tools)

El servidor expone 9 herramientas que los agentes pueden invocar:

### intake_list_specs

Lista todas las specs disponibles en el directorio de specs.

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| *(ninguno)* | — | No requiere entrada |

Retorna la lista de nombres de specs encontradas.

---

### intake_show

Muestra un resumen de la spec: cantidad de requisitos, tareas, checks de aceptacion, riesgos y costos.

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| `spec_name` | Si | Nombre de la spec |

---

### intake_get_context

Obtiene el contenido de `context.md` de una spec.

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| `spec_name` | Si | Nombre de la spec |

---

### intake_get_tasks

Obtiene la lista de tareas con filtrado opcional por estado.

| Parametro | Requerido | Default | Descripcion |
|-----------|-----------|---------|-------------|
| `spec_name` | Si | — | Nombre de la spec |
| `status_filter` | No | `"all"` | Filtro de estado: `pending`, `in_progress`, `done`, `blocked`, `all` |

Ejemplo de uso por un agente:

```json
{
  "spec_name": "mi-feature",
  "status_filter": "pending"
}
```

---

### intake_update_task

Actualiza el estado de una tarea.

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| `spec_name` | Si | Nombre de la spec |
| `task_id` | Si | ID de la tarea (ej: `"1"`, `"TASK-001"`) |
| `status` | Si | Nuevo estado: `pending`, `in_progress`, `done`, `blocked` |
| `note` | No | Nota opcional sobre la actualizacion |

---

### intake_verify

Ejecuta los checks de verificacion de la spec. Retorna el resultado pass/fail de cada check.

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| `spec_name` | Si | Nombre de la spec |
| `tags` | No | Array de tags para filtrar checks (ej: `["api", "tests"]`) |

---

### intake_feedback

Analiza los fallos de verificacion y sugiere correcciones. Internamente ejecuta verificacion, filtra los checks fallidos, y usa el modulo de feedback para generar sugerencias.

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| `spec_name` | Si | Nombre de la spec |

---

### intake_validate

Valida la consistencia interna de una spec: cross-references, dependencias de tareas, validez de checks de aceptacion y completeness. Funciona offline.

| Parametro | Requerido | Default | Descripcion |
|-----------|-----------|---------|-------------|
| `spec_name` | Si | — | Nombre de la spec |
| `strict` | No | `false` | Modo estricto: warnings se convierten en errores |

Retorna un reporte con errores, warnings, y conteos de requisitos, tareas y checks encontrados.

---

### intake_estimate

Estima el costo LLM para generar o regenerar una spec basandose en los archivos existentes.

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| `spec_name` | Si | Nombre de la spec |

Escanea los archivos de la spec para contar palabras y estima tokens, numero de llamadas LLM y costo en dolares.

---

## Recursos (Resources)

Los recursos permiten acceder directamente a los archivos de una spec mediante URIs con esquema `intake://`. Los recursos se auto-descubren: el servidor escanea el directorio de specs y registra todos los archivos disponibles.

### URIs disponibles

| URI | Archivo |
|-----|---------|
| `intake://specs/{name}/requirements` | `requirements.md` |
| `intake://specs/{name}/tasks` | `tasks.md` |
| `intake://specs/{name}/context` | `context.md` |
| `intake://specs/{name}/acceptance` | `acceptance.yaml` |
| `intake://specs/{name}/design` | `design.md` |
| `intake://specs/{name}/sources` | `sources.md` |

Donde `{name}` es el nombre del directorio de la spec dentro del directorio base de specs.

### Ejemplo

Si el directorio de specs es `./specs` y contiene:

```
specs/
├── auth-module/
│   ├── requirements.md
│   ├── tasks.md
│   ├── context.md
│   ├── acceptance.yaml
│   ├── design.md
│   └── sources.md
└── payment-api/
    ├── requirements.md
    └── ...
```

Los recursos disponibles serian:

- `intake://specs/auth-module/requirements`
- `intake://specs/auth-module/tasks`
- `intake://specs/auth-module/context`
- `intake://specs/auth-module/acceptance`
- `intake://specs/auth-module/design`
- `intake://specs/auth-module/sources`
- `intake://specs/payment-api/requirements`
- ...

---

## Prompts

El servidor proporciona 2 prompts estructurados que guian al agente en flujos de trabajo comunes.

### implement_next_task

Prompt estructurado que carga `context.md`, `requirements.md` y `tasks.md`, e instruye al agente para:

1. Encontrar la siguiente tarea pendiente
2. Implementarla siguiendo la spec
3. Ejecutar verificacion
4. Actualizar el estado de la tarea
5. Repetir hasta completar todas las tareas

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| `spec_name` | Si | Nombre de la spec |

### verify_and_fix

Prompt que instruye al agente para:

1. Ejecutar verificacion completa
2. Analizar los checks fallidos
3. Corregir el codigo
4. Re-verificar hasta que todos los checks pasen

| Parametro | Requerido | Descripcion |
|-----------|-----------|-------------|
| `spec_name` | Si | Nombre de la spec |

---

## Configuracion

El servidor MCP se configura en `.intake.yaml`:

```yaml
mcp:
  specs_dir: ./specs        # Directorio base para specs
  project_dir: .            # Directorio del proyecto para verificacion
  transport: stdio           # stdio | sse
  sse_port: 8080            # Puerto para el transporte SSE
```

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `specs_dir` | string | `"./specs"` | Directorio donde residen las specs generadas por intake |
| `project_dir` | string | `"."` | Directorio del proyecto contra el cual ejecutar verificacion |
| `transport` | string | `"stdio"` | Protocolo de transporte: `stdio` para agentes locales, `sse` para red |
| `sse_port` | int | `8080` | Puerto TCP para el servidor SSE |

Los flags de la CLI (`--specs-dir`, `--project-dir`, `--transport`, `--port`) sobreescriben los valores de configuracion.

---

## Integracion con agentes

### Claude Code

**Opcion 1: `.mcp.json` en el proyecto** (recomendado para Claude Code CLI)

```json
{
  "mcpServers": {
    "intake": {
      "command": "intake",
      "args": ["mcp", "serve", "--specs-dir", "./specs"]
    }
  }
}
```

Commitear `.mcp.json` en el repo para que todo el equipo tenga acceso al servidor MCP automaticamente.

**Opcion 2: `claude_desktop_config.json`** (para Claude Desktop)

```json
{
  "mcpServers": {
    "intake": {
      "command": "intake",
      "args": ["mcp", "serve", "--specs-dir", "./specs"]
    }
  }
}
```

Con esta configuracion, Claude Code puede:

1. Listar specs disponibles con `intake_list_specs`
2. Leer contexto y requisitos via recursos `intake://`
3. Consultar tareas pendientes con `intake_get_tasks`
4. Marcar tareas como completadas con `intake_update_task`
5. Verificar la implementacion con `intake_verify`
6. Obtener sugerencias de correccion con `intake_feedback`

### Otros clientes MCP

Cualquier cliente compatible con MCP puede conectarse:

**stdio** — el cliente lanza el proceso directamente:

```bash
intake mcp serve --specs-dir ./specs
```

**SSE** — el cliente se conecta via HTTP:

```bash
# Iniciar el servidor
intake mcp serve --transport sse --port 9090

# El cliente se conecta a http://localhost:9090/sse
```

---

## Arquitectura

### Modulos

| Archivo | Responsabilidad |
|---------|-----------------|
| `mcp/__init__.py` | Excepcion `MCPError` y exports publicos |
| `mcp/server.py` | Creacion del servidor, transportes stdio y SSE |
| `mcp/tools.py` | Definicion y handlers de las 9 herramientas |
| `mcp/resources.py` | Listado y lectura de recursos (archivos spec) |
| `mcp/prompts.py` | 2 plantillas de prompts estructurados |

### Dependencias

El modulo `mcp/` utiliza:

- `verify/` — para ejecutar checks de aceptacion (`intake_verify`)
- `utils/task_state` — para leer y actualizar estado de tareas (`intake_get_tasks`, `intake_update_task`)
- `feedback/` — para analisis de fallos (`intake_feedback`)
- `validate/` — para validacion interna de specs (`intake_validate`)
- `estimate/` — para estimacion de costos (`intake_estimate`)

El modulo `mcp/` **no importa** directamente de `analyze/` ni de `llm/`. La herramienta `intake_feedback` delega al modulo de feedback, que gestiona su propia interaccion con el LLM.

```
mcp/
  ├── tools.py → verify/, validate/, estimate/, utils/task_state, feedback/
  ├── resources.py → (lectura directa de archivos)
  └── prompts.py → (plantillas estaticas)
```

---

## Solucion de problemas

### El paquete `mcp` no esta instalado

```
Error: MCP dependencies not installed. Run: pip install "intake-ai-cli[mcp]"
```

**Solucion:** Instalar las dependencias MCP:

```bash
pip install "intake-ai-cli[mcp]"
```

Verificar con `intake doctor`.

### Spec no encontrada

```
Error: Spec 'mi-feature' not found in ./specs
```

**Solucion:** Verificar que el directorio de specs existe y contiene subdirectorios con archivos spec:

```bash
ls ./specs/
# Debe mostrar directorios como: mi-feature/

ls ./specs/mi-feature/
# Debe contener: requirements.md, tasks.md, context.md, etc.
```

Si las specs estan en otro directorio, usar `--specs-dir`:

```bash
intake mcp serve --specs-dir /path/to/specs
```

### Puerto SSE en uso

```
Error: Address already in use: port 8080
```

**Solucion:** Otro proceso esta usando el puerto. Opciones:

1. Usar un puerto diferente:
   ```bash
   intake mcp serve --transport sse --port 9090
   ```

2. Encontrar y detener el proceso que ocupa el puerto:
   ```bash
   lsof -i :8080
   kill <PID>
   ```

### Dependencias SSE faltantes

Si se usa transporte SSE sin `starlette` o `uvicorn`:

```
Error: SSE transport requires 'starlette' and 'uvicorn'. Install them with: pip install starlette uvicorn
```

**Solucion:**

```bash
pip install starlette uvicorn
```

### La verificacion falla desde MCP

Si `intake_verify` retorna errores, verificar que `--project-dir` apunta al directorio correcto del proyecto:

```bash
intake mcp serve --specs-dir ./specs --project-dir /path/to/project
```

Los checks de aceptacion se ejecutan relativos al directorio del proyecto.
