# Solucion de problemas

Guia para diagnosticar y resolver problemas comunes con intake.

---

## intake doctor

El primer paso ante cualquier problema es ejecutar `intake doctor`:

```bash
intake doctor
```

Esto verifica:

| Check | Que verifica | Auto-fixable |
|-------|-------------|--------------|
| Python version | Python >= 3.12 | No |
| LLM API key | Variable de entorno configurada | No |
| pdfplumber | Paquete instalado | Si |
| python-docx | Paquete instalado | Si |
| beautifulsoup4 | Paquete instalado | Si |
| markdownify | Paquete instalado | Si |
| litellm | Paquete instalado | Si |
| jinja2 | Paquete instalado | Si |
| Config file | `.intake.yaml` valido | Si |
| Jira credentials | `JIRA_API_TOKEN` + `JIRA_EMAIL` (si jira configurado) | No |
| Confluence credentials | `CONFLUENCE_API_TOKEN` + `CONFLUENCE_EMAIL` (si confluence configurado) | No |
| GitHub token | `GITHUB_TOKEN` (si github configurado) | No |

### Auto-fix

Para corregir automaticamente los problemas que se pueden resolver:

```bash
intake doctor --fix
```

Esto:

- **Instala paquetes faltantes** usando `pip3.12`, `pip3` o `pip` (en ese orden de preferencia)
- **Crea `.intake.yaml`** si no existe, con configuracion basica

---

## Errores comunes

### API key no configurada

**Error:**
```
LLM error: Environment variable ANTHROPIC_API_KEY is not set.
  Hint: Set it with: export ANTHROPIC_API_KEY=your-api-key
```

**Solucion:**

```bash
# Anthropic
export ANTHROPIC_API_KEY=sk-ant-api03-tu-key-aqui

# OpenAI
export OPENAI_API_KEY=sk-tu-key-aqui
```

Si usas otro proveedor, configura `llm.api_key_env` en `.intake.yaml`:

```yaml
llm:
  model: gemini/gemini-pro
  api_key_env: GEMINI_API_KEY
```

Verifica con:
```bash
intake doctor
```

---

### Archivo no encontrado

**Error:**
```
Failed to parse 'reqs.md': File not found: reqs.md
  Hint: Check that the file exists and the path is correct.
```

**Solucion:** Verifica que el path al archivo es correcto. Usa paths relativos al directorio actual o paths absolutos:

```bash
# Relativo
intake init "Feature" -s ./docs/reqs.md

# Absoluto
intake init "Feature" -s /home/user/project/docs/reqs.md
```

---

### Archivo vacio

**Error:**
```
Failed to parse 'empty.md': File is empty or contains only whitespace
  Hint: Provide a file with actual content.
```

**Solucion:** El archivo existe pero no tiene contenido util. Agrega contenido al archivo antes de usarlo como fuente.

---

### Archivo demasiado grande

**Error:**
```
Failed to parse 'huge.pdf': File size 52428800 bytes exceeds limit of 50 MB
  Hint: Split the file into smaller parts or extract the relevant sections.
```

**Solucion:** El limite es 50 MB. Opciones:

- Dividir el archivo en partes mas pequenas
- Extraer solo las secciones relevantes
- Si es un PDF, extraer las paginas necesarias con otra herramienta

---

### URL no accesible

**Error:**
```
Failed to parse 'https://example.com/page': Connection error: ...
  Hint: Check that the URL is correct and accessible.
```

**Solucion:** intake no pudo descargar la pagina. Verifica:

1. Que la URL es correcta y accesible desde tu red
2. Que no requiere autenticacion (intake no soporta URLs con login)
3. Que no hay un firewall o proxy bloqueando la conexion

Si la pagina requiere autenticacion, descarga el contenido manualmente y usa el archivo local:

```bash
# En vez de
intake init "Feature" -s https://internal-wiki.com/page  # falla si requiere login

# Descarga manualmente y usa el archivo
curl -o page.html https://internal-wiki.com/page
intake init "Feature" -s page.html
```

---

### Conector no puede conectar

**Error:**
```
Connector error: Failed to connect to Jira at https://company.atlassian.net
  Hint: Check connectors.jira.url and credentials in .intake.yaml
```

**Solucion:**

1. Verificar que la URL base es correcta en `.intake.yaml`:
   ```yaml
   connectors:
     jira:
       url: "https://company.atlassian.net"
   ```

2. Verificar que las variables de entorno estan configuradas:
   ```bash
   echo $JIRA_API_TOKEN    # debe tener un valor
   echo $JIRA_EMAIL        # debe tener un valor
   ```

3. Ejecutar `intake doctor` para validar credenciales de conectores.

4. Si la API requiere VPN o firewall, verificar la conexion de red.

### Conector no disponible (dependencia faltante)

**Error:**
```
Connector 'jira' requires atlassian-python-api.
  Hint: Install with: pip install "intake-ai-cli[connectors]"
```

**Solucion:**

```bash
# Instalar dependencias de conectores
pip install "intake-ai-cli[connectors]"
```

Los paquetes opcionales para conectores son:

| Conector | Paquete | Instalacion |
|----------|---------|-------------|
| Jira | atlassian-python-api | `pip install atlassian-python-api` |
| Confluence | atlassian-python-api | `pip install atlassian-python-api` |
| GitHub | PyGithub | `pip install PyGithub` |

**Alternativa sin instalar conectores:** Exporta los datos manualmente:

1. **Jira**: Exporta issues como JSON desde la interfaz web
2. **Confluence**: Exporta la pagina como HTML
3. **GitHub**: Usa `gh api repos/org/repo/issues > issues.json`

---

### Formato no soportado

**Error:**
```
Unsupported format: 'xlsx' for source 'data.xlsx'
```

**Solucion:** intake no soporta archivos Excel directamente. Opciones:

- Exportar a CSV o JSON desde Excel
- Copiar el contenido a un archivo de texto o Markdown
- Convertir a otro formato soportado (ver [Formatos de entrada](formatos-entrada.md))

---

### Presupuesto excedido

**Error:**
```
LLM error: Accumulated cost $0.5123 exceeds limit of $0.50
  Hint: Increase llm.max_cost_per_spec in your config, or use a cheaper model.
```

**Solucion:** El analisis supero el presupuesto configurado. Opciones:

1. **Aumentar el limite:**
   ```yaml
   llm:
     max_cost_per_spec: 1.00
   ```

2. **Usar un modelo mas barato:**
   ```bash
   intake init "Feature" -s reqs.md -m gpt-3.5-turbo
   ```

3. **Desactivar evaluacion de riesgos** (ahorra ~30%):
   ```yaml
   spec:
     risk_assessment: false
   ```

4. **Usar preset minimal:**
   ```bash
   intake init "Feature" -s reqs.md --preset minimal
   ```

---

### LLM no retorna JSON valido

**Error:**
```
LLM error: LLM did not return valid JSON after 3 attempts
  Hint: Try a different model or simplify the prompt.
```

**Solucion:** El modelo no pudo generar JSON valido despues de los reintentos configurados. Opciones:

1. **Intentar con otro modelo** — algunos modelos son mejores generando JSON estructurado:
   ```bash
   intake init "Feature" -s reqs.md -m claude-sonnet-4
   ```

2. **Aumentar reintentos:**
   ```yaml
   llm:
     max_retries: 5
   ```

3. **Reducir la temperatura** para output mas determinista:
   ```yaml
   llm:
     temperature: 0.1
   ```

4. **Simplificar las fuentes** — textos muy largos o complejos pueden confundir al modelo.

---

### Timeout del LLM

**Error:**
```
LLM failed after 3 attempts: Request timed out
  Hint: Check your API key, network connection, and model name.
```

**Solucion:**

1. **Verificar conexion a internet**
2. **Aumentar el timeout:**
   ```yaml
   llm:
     timeout: 300  # 5 minutos
   ```
3. **Verificar que el modelo existe** — nombres incorrectos causan timeout:
   ```yaml
   # Correcto
   llm:
     model: claude-sonnet-4

   # Incorrecto — causara timeout o error
   llm:
     model: claude-sonet-4  # typo
   ```

---

### Error de encoding

Si un archivo tiene encoding no-UTF-8, intake intenta leerlo con fallback a latin-1. Si aun asi falla:

**Solucion:**

1. Convertir el archivo a UTF-8:
   ```bash
   iconv -f ISO-8859-1 -t UTF-8 archivo.txt > archivo_utf8.txt
   ```

2. O abrir en un editor y guardar como UTF-8.

---

### PDF sin texto extraible

**Error:**
```
Failed to parse 'scanned.pdf': PDF contains only scanned images, no extractable text
  Hint: Use an image source instead.
```

**Solucion:** El PDF contiene imagenes escaneadas, no texto digital. Opciones:

1. Usar OCR externo para extraer el texto primero
2. Exportar las paginas como imagenes y usar el parser de imagenes:
   ```bash
   intake init "Feature" -s pagina1.png -s pagina2.png
   ```

---

### Paquete faltante para parser

**Error:**
```
PDF parsing requires pdfplumber.
  Hint: Install it with: pip install pdfplumber
```

**Solucion:**

```bash
# Instalar manualmente
pip install pdfplumber

# O usar doctor --fix para instalar todo lo faltante
intake doctor --fix
```

Paquetes opcionales por parser:

| Parser | Paquete | Instalacion |
|--------|---------|-------------|
| PDF | pdfplumber | `pip install pdfplumber` |
| DOCX | python-docx | `pip install python-docx` |
| Confluence | beautifulsoup4, markdownify | `pip install beautifulsoup4 markdownify` |
| URLs | httpx, beautifulsoup4, markdownify | `pip install httpx beautifulsoup4 markdownify` |

---

### Plugin no se carga

**Error visible con:**
```bash
intake plugins list -v   # La columna "Error" muestra el detalle
intake plugins check     # Reporta FAIL con detalles
```

**Solucion:**

1. **Plugin externo no instalado**: verifica que el paquete esta instalado en el mismo entorno:
   ```bash
   pip list | grep mi-plugin
   ```

2. **Entry point mal configurado**: verifica que `pyproject.toml` tiene el entry_point correcto:
   ```toml
   [project.entry-points."intake.parsers"]
   mi-formato = "mi_plugin.parser:MiParser"
   ```

3. **Error de importacion**: el modulo del plugin falla al importar. Verifica las dependencias del plugin.

4. **Reinstalar**: a veces los entry_points no se actualizan sin reinstalar:
   ```bash
   pip install -e .
   ```

---

### acceptance.yaml invalido

**Error:**
```
Verification failed: Invalid YAML in acceptance.yaml: ...
  Hint: Check acceptance.yaml syntax.
```

**Solucion:** El archivo `acceptance.yaml` tiene errores de sintaxis YAML. Verificar:

- Indentacion correcta (usar espacios, no tabs)
- Strings con caracteres especiales entre comillas
- Listas con `-` seguido de espacio

```yaml
# Correcto
checks:
  - id: check-01
    name: "Tests pasan"
    type: command
    command: "python -m pytest tests/ -q"

# Incorrecto — falta espacio despues de -
checks:
  -id: check-01
```

---

## FAQ

### Necesito internet para usar intake?

Solo para `intake init` y `intake add` (que requieren llamadas al LLM). Todo lo demas funciona offline:

- `intake verify` — ejecuta checks localmente
- `intake export` — genera archivos localmente
- `intake show` / `intake list` — lee archivos locales
- `intake diff` — compara archivos locales
- `intake doctor` — verifica el entorno local

### Puedo usar modelos locales?

Si. intake usa LiteLLM, que soporta modelos locales via Ollama, vLLM, y otros:

```yaml
llm:
  model: ollama/llama3
  api_key_env: DUMMY_KEY  # Ollama no necesita key
```

```bash
export DUMMY_KEY=not-needed
intake init "Feature" -s reqs.md
```

### En que idioma se genera la spec?

Por defecto en ingles (`en`). Se configura con `--lang` o `project.language`:

```bash
intake init "Feature" -s reqs.md --lang es
```

```yaml
project:
  language: es
```

El idioma afecta al contenido generado por el LLM, no a la estructura de los archivos.

### Cuanto cuesta generar una spec?

Depende del modelo, la cantidad de texto, y las opciones habilitadas:

| Escenario | Costo aproximado |
|-----------|------------------|
| Fuente pequena, preset minimal, Claude Sonnet | ~$0.02-0.05 |
| Fuente mediana, preset standard, Claude Sonnet | ~$0.05-0.15 |
| Multiples fuentes, preset enterprise, Claude Sonnet | ~$0.15-0.50 |
| GPT-3.5 en vez de Claude | ~50-70% menos |

Usa `intake show` para ver el costo real despues de generar.

### Puedo editar las specs generadas?

Si. Las specs son archivos Markdown y YAML normales. Puedes editarlos manualmente despues de generarlos. Sin embargo, si usas `intake add --regenerate`, tus ediciones manuales se sobreescribiran.

### Como actualizo una spec con nuevos requisitos?

```bash
# Agregar una fuente nueva
intake add specs/mi-feature/ -s nuevos-reqs.md

# O regenerar todo con la nueva fuente
intake add specs/mi-feature/ -s nuevos-reqs.md --regenerate
```

### Puedo usar intake en CI/CD?

Si. Ver la seccion de [integracion CI/CD](verificacion.md#integracion-con-cicd) en la guia de verificacion.

### Los archivos spec se deben commitear a git?

Si, es recomendable. Las specs son archivos de texto que se benefician del versionado. Ver [Versionado de specs](buenas-practicas.md#versionado-de-specs).

### Que es el modo quick / standard / enterprise?

intake auto-detecta la complejidad de tus fuentes y selecciona un modo de generacion:

- **quick** (<500 palabras, 1 fuente simple): solo genera `context.md` + `tasks.md`
- **standard** (default): genera los 6 archivos spec completos
- **enterprise** (4+ fuentes o >5000 palabras): todos los archivos + riesgos detallados

Puedes forzar un modo con `--mode`:

```bash
intake init "Fix rapido" -s bug.txt --mode quick
```

### Como instalo plugins externos?

Los plugins se descubren automaticamente al instalar paquetes que registran entry_points en los grupos `intake.parsers`, `intake.exporters`, o `intake.connectors`:

```bash
pip install mi-plugin-intake
intake plugins list   # deberia aparecer el nuevo plugin
```

Ver [Plugins](plugins.md) para mas detalles.

### Como veo el progreso de las tareas?

```bash
intake task list specs/mi-feature/
intake task update specs/mi-feature/ 1 done --note "Completado"
```
