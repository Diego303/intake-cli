# Conectores

Los conectores API directos permiten obtener datos desde Jira, Confluence y GitHub sin exportar archivos manualmente. Se usan mediante URIs de esquema en el flag `-s`.

```bash
intake init "Sprint tasks" -s jira://PROJ/sprint/42
intake init "RFC review" -s confluence://ENG/Architecture-RFC
intake init "Bug triage" -s github://org/repo/issues?labels=bug
```

---

## Requisitos previos

### Instalacion

Los conectores requieren dependencias opcionales:

```bash
pip install "intake-ai-cli[connectors]"
```

Esto instala `atlassian-python-api` (Jira, Confluence) y `PyGithub` (GitHub).

### Configuracion

Configura las credenciales en `.intake.yaml` y variables de entorno:

```yaml
connectors:
  jira:
    url: "https://company.atlassian.net"
    token_env: JIRA_API_TOKEN
    email_env: JIRA_EMAIL
  confluence:
    url: "https://company.atlassian.net/wiki"
    token_env: CONFLUENCE_API_TOKEN
    email_env: CONFLUENCE_EMAIL
  github:
    token_env: GITHUB_TOKEN
```

```bash
export JIRA_API_TOKEN=tu-api-token
export JIRA_EMAIL=dev@company.com
export CONFLUENCE_API_TOKEN=tu-api-token
export CONFLUENCE_EMAIL=dev@company.com
export GITHUB_TOKEN=ghp_tu-personal-access-token
```

### Verificacion

```bash
intake doctor    # verifica credenciales si los conectores estan configurados
```

---

## Jira

Obtiene issues directamente de la API REST de Jira Cloud o Server.

### URIs soportadas

| URI | Que hace |
|-----|---------|
| `jira://PROJ-123` | Un solo issue |
| `jira://PROJ-123,PROJ-124,PROJ-125` | Multiples issues separados por coma |
| `jira://PROJ?jql=sprint%20%3D%2042` | Busqueda JQL |
| `jira://PROJ/sprint/42` | Todos los issues de un sprint |

### Ejemplos

```bash
# Un issue especifico
intake init "Fix auth bug" -s jira://AUTH-456

# Multiples issues
intake init "Sprint review" -s jira://AUTH-456,AUTH-457,AUTH-458

# Busqueda JQL
intake init "P1 bugs" -s "jira://PROJ?jql=priority=Highest AND status!=Done"

# Sprint completo
intake init "Sprint 42" -s jira://PROJ/sprint/42
```

### Configuracion completa

```yaml
connectors:
  jira:
    url: "https://company.atlassian.net"     # Requerido
    auth_type: token                          # token | oauth | api_key
    token_env: JIRA_API_TOKEN                 # Nombre de la variable de entorno
    email_env: JIRA_EMAIL                     # Email para autenticacion
    default_project: ""                       # Proyecto por defecto
    include_comments: true                    # Incluir comentarios
    max_comments: 5                           # Maximo de comentarios por issue
    fields:                                   # Campos a recuperar
      - summary
      - description
      - labels
      - priority
      - status
      - issuelinks
      - comment
```

### Que extrae

Por cada issue, el conector obtiene los mismos datos que `JiraParser` extrae de archivos JSON:

- Summary, description, priority, status
- Labels y issue links (dependencias)
- Comentarios (hasta `max_comments`, con soporte ADF)

Los datos se guardan como archivos JSON temporales compatibles con `JiraParser`.

---

## Confluence

Obtiene paginas directamente de la API de Confluence Cloud o Server.

### URIs soportadas

| URI | Que hace |
|-----|---------|
| `confluence://page/123456789` | Pagina por ID |
| `confluence://SPACE/Page-Title` | Pagina por space y titulo |
| `confluence://search?cql=space.key%3DENG` | Busqueda CQL |

### Ejemplos

```bash
# Pagina por ID
intake init "RFC review" -s confluence://page/123456789

# Pagina por space y titulo
intake init "Architecture" -s confluence://ENG/System-Architecture

# Busqueda CQL
intake init "Team docs" -s "confluence://search?cql=space.key=ENG AND label=requirements"
```

### Configuracion completa

```yaml
connectors:
  confluence:
    url: "https://company.atlassian.net/wiki"  # Requerido
    auth_type: token                            # token | oauth
    token_env: CONFLUENCE_API_TOKEN
    email_env: CONFLUENCE_EMAIL
    default_space: ""                           # Space por defecto
    include_child_pages: false                  # Incluir paginas hijas
    max_depth: 1                                # Profundidad maxima
```

### Que extrae

El conector descarga el body de la pagina en formato HTML (storage o view format) y lo guarda como archivo HTML temporal compatible con `ConfluenceParser`. Extrae:

- Contenido HTML de la pagina
- Titulo y metadata
- Paginas hijas (si `include_child_pages: true`)

---

## GitHub

Obtiene issues directamente de la API de GitHub.

### URIs soportadas

| URI | Que hace |
|-----|---------|
| `github://org/repo/issues/42` | Un solo issue |
| `github://org/repo/issues/42,43,44` | Multiples issues separados por coma |
| `github://org/repo/issues?labels=bug&state=open` | Issues filtrados |

### Parametros de filtrado

| Parametro | Descripcion | Ejemplo |
|-----------|-------------|---------|
| `labels` | Filtrar por labels (separados por coma) | `labels=bug,urgent` |
| `state` | Estado del issue | `state=open`, `state=closed`, `state=all` |
| `milestone` | Filtrar por milestone | `milestone=v2.0` |

### Ejemplos

```bash
# Un issue especifico
intake init "Fix #42" -s github://org/repo/issues/42

# Multiples issues
intake init "Sprint items" -s github://org/repo/issues/42,43,44

# Todos los bugs abiertos
intake init "Bug triage" -s "github://org/repo/issues?labels=bug&state=open"

# Issues de un milestone
intake init "v2.0 features" -s "github://org/repo/issues?milestone=v2.0&state=all"
```

### Configuracion completa

```yaml
connectors:
  github:
    token_env: GITHUB_TOKEN      # Variable de entorno con el PAT
    default_repo: ""              # Repo por defecto (ej: "org/repo")
```

### Limites

- Maximo **50 issues** por consulta
- Maximo **10 comentarios** por issue
- Requiere un Personal Access Token con permisos de lectura en el repositorio

### Que extrae

Los issues se guardan como JSON temporal compatible con `GithubIssuesParser`:

- Number, title, body, state
- Labels, assignees, milestone
- Comentarios (hasta 10 por issue)
- Cross-references (`#NNN`) en body y comments

---

## Protocol

Los conectores implementan el protocolo `ConnectorPlugin`:

```python
@runtime_checkable
class ConnectorPlugin(Protocol):
    @property
    def meta(self) -> PluginMeta: ...

    @property
    def uri_schemes(self) -> list[str]: ...

    def can_handle(self, uri: str) -> bool: ...
    async def fetch(self, uri: str) -> list[FetchedSource]: ...
    def validate_config(self) -> list[str]: ...
```

El metodo `fetch()` es async y retorna una lista de `FetchedSource`:

```python
@dataclass
class FetchedSource:
    local_path: str          # Path al archivo temporal descargado
    original_uri: str        # URI original (ej: "jira://PROJ-123")
    format_hint: str         # Hint para el parser (ej: "jira", "confluence")
    metadata: dict[str, str] # Metadata adicional
```

Los archivos temporales se pasan al registry de parsers para ser procesados normalmente.

---

## Crear un conector externo

1. Crear un paquete Python que implemente `ConnectorPlugin`
2. Registrar como entry_point en el grupo `intake.connectors`
3. El conector sera descubierto automaticamente

```toml
# pyproject.toml
[project.entry-points."intake.connectors"]
asana = "mi_plugin.connector:AsanaConnector"
```

Ver [Plugins](plugins.md) para mas detalles.
