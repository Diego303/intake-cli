# Guia CLI

intake proporciona 15 comandos y subcomandos. Todos siguen el patron:

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
   - URIs de esquema (`jira://`, `confluence://`, `github://`) → se resuelven via conectores API (ver [Conectores](conectores.md))
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

Detecta subdirectorios que contengan `requirements.md` o `acceptance.yaml`.

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
| LLM API key | `ANTHROPIC_API_KEY` o `OPENAI_API_KEY` definida | No |
| pdfplumber | Paquete instalado | Si |
| python-docx | Paquete instalado | Si |
| beautifulsoup4 | Paquete instalado | Si |
| markdownify | Paquete instalado | Si |
| litellm | Paquete instalado | Si |
| jinja2 | Paquete instalado | Si |
| Config file | `.intake.yaml` existe y es YAML valido | Si (crea uno basico) |

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

## Opciones globales

| Flag | Descripcion |
|------|-------------|
| `--version` | Muestra la version de intake |
| `--help` | Muestra la ayuda del comando |

```bash
intake --version    # intake, version 0.3.0
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
