# Formatos de entrada

intake soporta 8 formatos de entrada a traves de parsers especializados. El formato se auto-detecta por extension de archivo y contenido.

---

## Tabla resumen

| Formato | Parser | Extensiones | Dependencia | Que extrae |
|---------|--------|-------------|-------------|-----------|
| Markdown | `MarkdownParser` | `.md`, `.markdown` | — | Front matter YAML, secciones por headings |
| Texto plano | `PlaintextParser` | `.txt`, stdin (`-`) | — | Parrafos como secciones |
| YAML / JSON | `YamlInputParser` | `.yaml`, `.yml`, `.json` | — | Claves top-level como secciones |
| PDF | `PdfParser` | `.pdf` | pdfplumber | Texto por pagina, tablas como Markdown |
| DOCX | `DocxParser` | `.docx` | python-docx | Parrafos, tablas, metadata, secciones por headings |
| Jira | `JiraParser` | `.json` (auto-detectado) | — | Issues, comments, links, labels, prioridad |
| Confluence | `ConfluenceParser` | `.html`, `.htm` (auto-detectado) | bs4, markdownify | Contenido limpio como Markdown |
| Imagenes | `ImageParser` | `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif` | LLM vision | Descripcion del contenido visual |

---

## Auto-deteccion de formato

El registry detecta el formato automaticamente siguiendo este orden:

1. **Stdin** (`-`): siempre se trata como `plaintext`
2. **Extension del archivo**: mapeo directo (`.md` -> markdown, `.pdf` -> pdf, etc.)
3. **Subtipo JSON**: si la extension es `.json`:
   - Si tiene key `"issues"` o es una lista con objetos que tienen `"key"` + `"fields"` -> `jira`
   - Si no -> `yaml` (se trata como datos estructurados)
4. **Subtipo HTML**: si la extension es `.html` o `.htm`:
   - Si los primeros 2000 caracteres contienen "confluence" o "atlassian" -> `confluence`
   - Si no -> fallback a `plaintext`
5. **Fallback**: si no hay parser para el formato detectado -> `plaintext`

---

## Parsers en detalle

### Markdown

**Extensiones:** `.md`, `.markdown`

**Que extrae:**

- **YAML front matter**: si el archivo empieza con `---`, extrae los metadatos como pares clave-valor
- **Secciones por headings**: cada `#`, `##`, `###`, etc. se convierte en una seccion con titulo, nivel y contenido
- **Texto completo**: el contenido sin el front matter

**Ejemplo de fuente:**

```markdown
---
project: API de Usuarios
version: 2.0
priority: high
---

# Requisitos Funcionales

## FR-01: Registro de usuarios
El sistema debe permitir registro con email y password...

## FR-02: Autenticacion
El sistema debe soportar OAuth2 y JWT...
```

**Metadata extraida:** `project`, `version`, `priority` (del front matter)

---

### Texto plano

**Extensiones:** `.txt`, stdin (`-`), archivos sin extension

**Que extrae:**

- **Secciones por parrafos**: cada bloque separado por lineas en blanco se convierte en una seccion
- **Metadata**: `source_type` ("stdin" o "file")

**Ideal para:**

- Notas rapidas
- Dumps de Slack
- Ideas en bruto
- Texto copiado desde cualquier fuente

**Ejemplo:**

```text
Necesitamos un sistema de notificaciones en tiempo real.
Debe soportar WebSocket para updates inmediatos.

Los usuarios deben poder configurar sus preferencias:
- Email para notificaciones importantes
- Push para updates en tiempo real
- Silenciar por horario
```

---

### YAML / JSON

**Extensiones:** `.yaml`, `.yml`, `.json` (cuando no es Jira)

**Que extrae:**

- **Secciones por claves top-level**: cada clave de primer nivel se convierte en una seccion
- **Texto**: representacion YAML del contenido completo
- **Metadata**: `top_level_keys` (cantidad) o `item_count`

**Ejemplo de fuente:**

```yaml
functional_requirements:
  - id: FR-01
    title: User Registration
    description: Users must be able to register...
    priority: high
    acceptance_criteria:
      - Email validation
      - Password strength check

non_functional_requirements:
  - id: NFR-01
    title: API Response Time
    description: All API endpoints must respond in under 200ms
```

---

### PDF

**Extensiones:** `.pdf`
**Requiere:** `pdfplumber`

**Que extrae:**

- **Texto por pagina**: cada pagina se convierte en una seccion
- **Tablas**: se convierten a formato Markdown automaticamente
- **Metadata**: `page_count`

**Limitaciones:**

- Solo funciona con PDFs que tienen texto extraible
- PDFs escaneados (solo imagenes) no son soportados directamente — usar el parser de imagenes en su lugar

---

### DOCX

**Extensiones:** `.docx`
**Requiere:** `python-docx`

**Que extrae:**

- **Parrafos**: texto de cada parrafo
- **Secciones por headings**: headings de Word se convierten en secciones estructuradas
- **Tablas**: se convierten a formato Markdown
- **Metadata del documento**: autor, titulo, asunto, fecha de creacion

---

### Jira

**Extensiones:** `.json` (auto-detectado por estructura)

Soporta dos formatos de exportacion de Jira:

**Formato API REST** (`{"issues": [...]}`):

```json
{
  "issues": [
    {
      "key": "PROJ-001",
      "fields": {
        "summary": "Implementar login",
        "description": "El usuario debe poder...",
        "priority": {"name": "High"},
        "status": {"name": "To Do"},
        "labels": ["auth", "mvp"],
        "comment": {
          "comments": [...]
        },
        "issuelinks": [...]
      }
    }
  ]
}
```

**Formato lista** (`[{"key": "...", "fields": {...}}, ...]`):

```json
[
  {
    "key": "PROJ-001",
    "fields": {
      "summary": "Implementar login",
      "description": "..."
    }
  }
]
```

**Que extrae por cada issue:**

| Dato | Campo Jira | Limite |
|------|-----------|--------|
| Summary | `fields.summary` | — |
| Description | `fields.description` | — |
| Priority | `fields.priority.name` | — |
| Status | `fields.status.name` | — |
| Labels | `fields.labels` | — |
| Comments | `fields.comment.comments` | Ultimos 5, max 500 chars cada uno |
| Issue links | `fields.issuelinks` | Tipo, direccion, target |

**Soporte ADF:** Los comentarios en Atlassian Document Format (JSON anidado) se convierten automaticamente a texto plano.

**Relaciones extraidas:**

- `blocks` / `is blocked by`
- `depends on`
- `relates to`

---

### Confluence

**Extensiones:** `.html`, `.htm` (auto-detectado por contenido)
**Requiere:** `beautifulsoup4`, `markdownify`

**Deteccion:** Los primeros 2000 caracteres del archivo se inspeccionan buscando "confluence" o "atlassian".

**Que extrae:**

- **Contenido principal**: busca el div de contenido principal (por id, clase, o rol)
- **Conversion a Markdown**: convierte HTML a Markdown limpio con headings ATX
- **Secciones por headings**: del Markdown resultante
- **Metadata**: titulo, autor, fecha, descripcion (de tags `<meta>`)

**Selectores de contenido** (en orden de prioridad):

1. `div#main-content`
2. `div.wiki-content`
3. `div.confluence-information-macro`
4. `div#content`
5. `div[role=main]`
6. `<body>` (fallback)

---

### Imagenes

**Extensiones:** `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`
**Requiere:** LLM con capacidad de vision

**Que hace:**

1. Codifica la imagen en base64
2. Envia al LLM vision con un prompt pidiendo describir:
   - Mockups de UI / wireframes
   - Diagramas de arquitectura
   - Texto visible en la imagen
3. Retorna la descripcion como texto

**Metadata:** `image_format`, `file_size_bytes`

**Nota:** Por defecto usa un stub que retorna texto placeholder. La vision real se activa cuando se configura el `LLMAdapter` con un modelo que soporte vision.

---

## Limitaciones generales

| Limite | Valor | Descripcion |
|--------|-------|-------------|
| Tamano maximo | 50 MB | Archivos mayores a 50 MB son rechazados con `FileTooLargeError` |
| Archivos vacios | Error | Archivos vacios o solo whitespace producen `EmptySourceError` |
| Encoding | UTF-8 + fallback | Intenta UTF-8 primero, fallback a latin-1 |
| Directorios | Error | Pasar un directorio como fuente produce un error |

---

## Agregar soporte para mas formatos

intake usa el patron `Protocol` para parsers. Para agregar un nuevo parser:

1. Crear un archivo en `src/intake/ingest/` (ej: `asana.py`)
2. Implementar los metodos `can_parse(source: str) -> bool` y `parse(source: str) -> ParsedContent`
3. Registrarlo en `registry.py` dentro de `create_default_registry()`

No es necesario heredar de ninguna clase base — solo implementar la interfaz correcta.
