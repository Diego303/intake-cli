# Formatos de entrada

intake soporta 12 formatos de entrada a traves de parsers especializados. El formato se auto-detecta por extension de archivo y contenido. Los parsers se descubren automaticamente via el [sistema de plugins](plugins.md).

---

## Tabla resumen

| Formato | Parser | Extensiones / Fuente | Dependencia | Que extrae |
|---------|--------|---------------------|-------------|-----------|
| Markdown | `MarkdownParser` | `.md`, `.markdown` | — | Front matter YAML, secciones por headings |
| Texto plano | `PlaintextParser` | `.txt`, stdin (`-`) | — | Parrafos como secciones |
| YAML / JSON | `YamlInputParser` | `.yaml`, `.yml`, `.json` | — | Claves top-level como secciones |
| PDF | `PdfParser` | `.pdf` | pdfplumber | Texto por pagina, tablas como Markdown |
| DOCX | `DocxParser` | `.docx` | python-docx | Parrafos, tablas, metadata, secciones por headings |
| Jira | `JiraParser` | `.json` (auto-detectado) | — | Issues, comments, links, labels, prioridad |
| Confluence | `ConfluenceParser` | `.html`, `.htm` (auto-detectado) | bs4, markdownify | Contenido limpio como Markdown |
| Imagenes | `ImageParser` | `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif` | LLM vision | Descripcion del contenido visual |
| URLs | `UrlParser` | `http://`, `https://` | httpx, bs4, markdownify | Contenido de paginas web como Markdown |
| Slack | `SlackParser` | `.json` (auto-detectado) | — | Mensajes, threads, decisiones, action items |
| GitHub Issues | `GithubIssuesParser` | `.json` (auto-detectado) | — | Issues, labels, comments, cross-references |
| GitLab Issues | `GitlabIssuesParser` | `.json` (auto-detectado) | — | Issues, labels, notes, milestones, merge requests |

---

## Auto-deteccion de formato

El registry detecta el formato automaticamente siguiendo este orden:

1. **Stdin** (`-`): siempre se trata como `plaintext`
2. **Extension del archivo**: mapeo directo (`.md` -> markdown, `.pdf` -> pdf, etc.)
3. **Subtipo JSON**: si la extension es `.json`, se inspecciona el contenido en este orden:
   - Si tiene key `"issues"` o es una lista con objetos que tienen `"key"` + `"fields"` -> `jira`
   - Si tiene campo `"iid"` (objeto o lista de objetos) -> `gitlab_issues`
   - Si es una lista con objetos que tienen `"number"` + (`"html_url"` o `"labels"`) -> `github_issues`
   - Si es una lista con objetos que tienen `"type": "message"` + `"ts"` -> `slack`
   - Si no matchea ningun subtipo -> `yaml` (se trata como datos estructurados)
4. **Subtipo HTML**: si la extension es `.html` o `.htm`:
   - Si los primeros 2000 caracteres contienen "confluence" o "atlassian" -> `confluence`
   - Si no -> fallback a `plaintext`
5. **URLs**: si la fuente empieza con `http://` o `https://` -> `url`
6. **Fallback**: si no hay parser para el formato detectado -> `plaintext`

**Nota:** La deteccion de subtipos JSON sigue un orden de prioridad estricto: Jira > GitLab Issues > GitHub Issues > Slack > YAML generico. Esto evita ambiguedades cuando un JSON tiene campos que podrian matchear multiples formatos.

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

### URLs

**Fuente:** URLs que empiezan con `http://` o `https://`
**Requiere:** `httpx`, `beautifulsoup4`, `markdownify`

**Que hace:**

1. Descarga la pagina via `httpx` (sync, timeout configurable)
2. Convierte HTML a Markdown limpio via BeautifulSoup4 + markdownify
3. Extrae titulo de la pagina, secciones por headings
4. Auto-detecta tipo de fuente por patrones en la URL

**Auto-deteccion de tipo:**

| Patron en URL | Tipo detectado |
|---------------|---------------|
| `confluence`, `wiki` | confluence |
| `jira`, `atlassian` | jira |
| `github.com` | github |
| Otros | webpage |

**Metadata extraida:** `url`, `title`, `source_type`, `section_count`

**Manejo de errores:**

- Timeout → `ParseError` con sugerencia de verificar la URL
- HTTP 4xx/5xx → `ParseError` con el codigo de estado
- Error de conexion → `ParseError` con sugerencia de verificar la red

**Ejemplo:**

```bash
intake init "API review" -s https://wiki.company.com/rfc/auth
```

---

### Slack

**Extensiones:** `.json` (auto-detectado por estructura)

**Deteccion:** El archivo JSON debe ser una lista de objetos con `"type": "message"` y campo `"ts"` (timestamp de Slack).

**Que extrae:**

- **Mensajes**: texto de cada mensaje con usuario y timestamp
- **Threads**: mensajes agrupados por `thread_ts`
- **Decisiones**: mensajes con reacciones especificas (thumbsup, white_check_mark) o keywords como "decidido", "agreed"
- **Action items**: mensajes con keywords como "TODO", "action item", "necesitamos"

**Metadata:**

| Campo | Descripcion |
|-------|-------------|
| `message_count` | Total de mensajes |
| `thread_count` | Cantidad de threads |
| `decision_count` | Decisiones detectadas |
| `action_item_count` | Action items detectados |

**Ejemplo de fuente:**

```json
[
  {"type": "message", "user": "U123", "text": "Necesitamos usar PostgreSQL", "ts": "1700000000.000"},
  {"type": "message", "user": "U456", "text": "De acuerdo", "ts": "1700000001.000",
   "reactions": [{"name": "thumbsup", "count": 3}]},
  {"type": "message", "user": "U789", "text": "TODO: configurar la base de datos", "ts": "1700000002.000",
   "thread_ts": "1700000000.000"}
]
```

---

### GitHub Issues

**Extensiones:** `.json` (auto-detectado por estructura)

**Deteccion:** El archivo JSON debe contener objetos con campo `"number"` y al menos `"html_url"`, `"title"` + `"labels"`, o `"title"` + `"body"`. Soporta tanto un solo issue como una lista.

**Que extrae:**

- **Issues**: numero, titulo, cuerpo, estado (open/closed)
- **Labels**: etiquetas del issue
- **Assignees**: usuarios asignados
- **Milestones**: hito asociado
- **Comments**: comentarios del issue
- **Cross-references**: detecta `#NNN` en el texto como referencias a otros issues

**Formatos soportados:**

```json
// Formato lista (multiples issues)
[
  {
    "number": 1,
    "title": "Bug en login",
    "body": "El login falla cuando...",
    "html_url": "https://github.com/org/repo/issues/1",
    "state": "open",
    "labels": [{"name": "bug"}, {"name": "priority:high"}],
    "comments": [
      {"body": "Reproducido en produccion", "user": {"login": "dev1"}}
    ]
  }
]

// Formato individual (un solo issue)
{
  "number": 42,
  "title": "Feature request",
  "body": "Necesitamos...",
  "html_url": "https://github.com/org/repo/issues/42"
}
```

**Metadata:** `source_type` ("github_issues"), `issue_count`, `labels` (lista separada por comas), `milestone` (si existe)

**Relaciones extraidas:** cross-references via `#NNN` en body y comments.

---

### GitLab Issues

**Extensiones:** `.json` (auto-detectado por estructura)

**Deteccion:** El archivo JSON debe contener objetos con campo `"iid"` (internal ID de GitLab). Soporta un solo issue, una lista, o un formato wrapped `{"issues": [...]}`.

**Que extrae:**

- **Issues**: IID, titulo, descripcion, estado (opened/closed)
- **Labels**: etiquetas del issue
- **Assignees**: usuarios asignados
- **Milestones**: hito asociado (titulo)
- **Weight**: peso del issue (si existe)
- **Task completion status**: progreso de checkboxes (count/completed_count)
- **Discussion notes**: notas de discusion no-sistema (max 500 chars cada una)
- **Merge requests**: MRs vinculados (como relaciones)

**Formatos soportados:**

```json
// Formato individual (un solo issue)
{
  "iid": 42,
  "title": "Implementar login SSO",
  "description": "El login debe soportar SAML...",
  "state": "opened",
  "labels": ["feature", "auth"],
  "milestone": {"title": "v2.0"},
  "assignees": [{"username": "jdoe"}],
  "notes": [
    {"author": {"username": "dev"}, "body": "Implementado", "system": false}
  ]
}

// Formato lista (multiples issues)
[
  {"iid": 42, "title": "...", ...},
  {"iid": 43, "title": "...", ...}
]

// Formato wrapped
{"issues": [{"iid": 42, ...}]}
```

**Metadata:** `source_type` ("gitlab_issues"), `issue_count`, `labels` (lista separada por comas), `milestone` (si existe)

**Relaciones extraidas:** Merge requests vinculados (si existen).

---

## Conectores API directos

Ademas de archivos locales, intake puede obtener datos directamente de APIs usando URIs de esquema. Los conectores requieren configuracion en `.intake.yaml` y credenciales via variables de entorno. Actualmente hay 4 conectores: Jira, Confluence, GitHub y GitLab.

### Jira

**URIs soportadas:**

| Patron | Que hace |
|--------|---------|
| `jira://PROJ-123` | Un solo issue |
| `jira://PROJ-123,PROJ-124,PROJ-125` | Multiples issues |
| `jira://PROJ?jql=sprint%20%3D%2042` | Busqueda JQL |
| `jira://PROJ/sprint/42` | Todos los issues de un sprint |

**Dependencia:** `atlassian-python-api` (instalar con `pip install "intake-ai-cli[connectors]"`)

**Ejemplo:**

```bash
intake init "Sprint 42 tasks" -s jira://PROJ/sprint/42
```

Los issues se descargan como JSON temporal y se parsean con `JiraParser`. Los comentarios se incluyen segun `connectors.jira.include_comments`.

### Confluence

**URIs soportadas:**

| Patron | Que hace |
|--------|---------|
| `confluence://page/123456789` | Pagina por ID |
| `confluence://SPACE/Page-Title` | Pagina por space y titulo |
| `confluence://search?cql=space.key%3DENG` | Busqueda CQL |

**Dependencia:** `atlassian-python-api`

**Ejemplo:**

```bash
intake init "Architecture RFC" -s confluence://ENG/Architecture-RFC-2025
```

Las paginas se descargan como HTML temporal y se parsean con `ConfluenceParser`.

### GitHub

**URIs soportadas:**

| Patron | Que hace |
|--------|---------|
| `github://org/repo/issues/42` | Un solo issue |
| `github://org/repo/issues/42,43,44` | Multiples issues |
| `github://org/repo/issues?labels=bug&state=open` | Issues filtrados por labels, estado, milestone |

**Dependencia:** `PyGithub` (instalar con `pip install "intake-ai-cli[connectors]"`)

**Ejemplo:**

```bash
intake init "Bug triage" -s github://org/repo/issues?labels=bug&state=open
```

Los issues se descargan como JSON temporal y se parsean con `GithubIssuesParser`. Maximo 50 issues por consulta, 10 comentarios por issue.

### GitLab

**URIs soportadas:**

| Patron | Que hace |
|--------|---------|
| `gitlab://group/project/issues/42` | Un solo issue |
| `gitlab://group/project/issues/42,43,44` | Multiples issues |
| `gitlab://group/project/issues?labels=bug&state=opened` | Issues filtrados |
| `gitlab://group/project/milestones/3/issues` | Issues de un milestone |

**Dependencia:** `python-gitlab` (instalar con `pip install "intake-ai-cli[connectors]"`)

**Ejemplo:**

```bash
intake init "Sprint review" -s gitlab://team/backend/issues?labels=sprint&state=opened
```

Los issues se descargan como JSON temporal y se parsean con `GitlabIssuesParser`. Maximo 50 issues por consulta, 10 notas por issue. Soporta grupos anidados y SSL configurable.

### Configuracion de conectores

Ver [Configuracion > Conectores](configuracion.md#seccion-connectors) para los campos de configuracion completos. Los conectores necesitan:

1. URL base de la instancia (Jira/Confluence) o token (GitHub)
2. Credenciales via variables de entorno
3. `intake doctor` verifica que las credenciales estan configuradas

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

Hay dos formas de agregar un nuevo parser:

### Opcion 1: Parser built-in (V1 Protocol)

1. Crear un archivo en `src/intake/ingest/` (ej: `asana.py`)
2. Implementar los metodos `can_parse(source: str) -> bool` y `parse(source: str) -> ParsedContent`
3. Registrarlo en `create_default_registry()` y como entry_point en `pyproject.toml`

### Opcion 2: Plugin externo (V2 ParserPlugin)

1. Crear un paquete Python separado
2. Implementar el protocolo `ParserPlugin` de `intake.plugins.protocols`
3. Registrar como entry_point en el grupo `intake.parsers` en tu `pyproject.toml`

El parser sera descubierto automaticamente al instalar el paquete. Ver [Plugins](plugins.md) para detalles.

No es necesario heredar de ninguna clase base — solo implementar la interfaz correcta (subtipado estructural via `typing.Protocol`).
