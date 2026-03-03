# Plugins

Desde v0.2.0, intake usa una arquitectura extensible basada en plugins. Los parsers, exporters y conectores se descubren automaticamente via entry_points de Python (PEP 621).

---

## Como funciona

### Descubrimiento automatico

intake usa `importlib.metadata.entry_points()` para descubrir plugins instalados. Cada plugin se registra en un **grupo de entry_points**:

| Grupo | Tipo | Ejemplo |
|-------|------|---------|
| `intake.parsers` | Parsers de formatos de entrada | `markdown = "intake.ingest.markdown:MarkdownParser"` |
| `intake.exporters` | Exporters de formatos de salida | `architect = "intake.export.architect:ArchitectExporter"` |
| `intake.connectors` | Conectores API directos | (vacio — preparacion para Fase 2) |

Cuando intake carga un registry (`ParserRegistry`, `ExporterRegistry`), intenta descubrir plugins primero. Si el descubrimiento falla, cae back a registro manual (hardcoded).

### Verificar plugins instalados

```bash
# Listar todos los plugins descubiertos
intake plugins list

# Con detalles (modulo, errores de carga)
intake plugins list -v

# Verificar compatibilidad
intake plugins check
```

---

## Plugins built-in

intake incluye 13 plugins built-in registrados como entry_points en `pyproject.toml`:

### Parsers (11)

| Nombre | Modulo | Formato |
|--------|--------|---------|
| `markdown` | `intake.ingest.markdown:MarkdownParser` | `.md`, `.markdown` |
| `plaintext` | `intake.ingest.plaintext:PlaintextParser` | `.txt`, stdin |
| `yaml` | `intake.ingest.yaml_input:YamlInputParser` | `.yaml`, `.yml`, `.json` |
| `pdf` | `intake.ingest.pdf:PdfParser` | `.pdf` |
| `docx` | `intake.ingest.docx:DocxParser` | `.docx` |
| `jira` | `intake.ingest.jira:JiraParser` | `.json` (auto-detectado) |
| `confluence` | `intake.ingest.confluence:ConfluenceParser` | `.html` (auto-detectado) |
| `image` | `intake.ingest.image:ImageParser` | `.png`, `.jpg`, `.webp`, `.gif` |
| `url` | `intake.ingest.url:UrlParser` | `http://`, `https://` |
| `slack` | `intake.ingest.slack:SlackParser` | `.json` (auto-detectado) |
| `github_issues` | `intake.ingest.github_issues:GithubIssuesParser` | `.json` (auto-detectado) |

### Exporters (2)

| Nombre | Modulo | Formato |
|--------|--------|---------|
| `architect` | `intake.export.architect:ArchitectExporter` | `pipeline.yaml` + spec |
| `generic` | `intake.export.generic:GenericExporter` | `SPEC.md` + `verify.sh` + spec |

---

## Protocolos

intake define dos generaciones de protocolos:

### V1 — Core Protocols

Los protocolos V1 son los originales del sistema. Son minimos y suficientes para parsers y exporters simples:

```python
# Parser V1
@runtime_checkable
class Parser(Protocol):
    def can_parse(self, source: str) -> bool: ...
    def parse(self, source: str) -> ParsedContent: ...

# Exporter V1
@runtime_checkable
class Exporter(Protocol):
    def export(self, spec_dir: str, output_dir: str) -> list[str]: ...
```

Todos los parsers y exporters built-in usan V1. Los registries aceptan tanto V1 como V2.

### V2 — Plugin Protocols

Los protocolos V2 extienden V1 con metadata, capacidades de descubrimiento, y funcionalidad adicional. Estan pensados para plugins externos:

```python
@runtime_checkable
class ParserPlugin(Protocol):
    @property
    def meta(self) -> PluginMeta: ...

    @property
    def supported_extensions(self) -> set[str]: ...

    def confidence(self, source: str) -> float: ...
    def can_parse(self, source: str) -> bool: ...
    def parse(self, source: str) -> ParsedContent: ...
```

```python
@runtime_checkable
class ExporterPlugin(Protocol):
    @property
    def meta(self) -> PluginMeta: ...

    @property
    def supported_agents(self) -> list[str]: ...

    def export(self, spec_dir: str, output_dir: str) -> ExportResult: ...
```

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

### Dataclasses de soporte

```python
@dataclass
class PluginMeta:
    name: str
    version: str
    description: str
    author: str

@dataclass
class ExportResult:
    files_created: list[str]
    primary_file: str
    instructions: str

@dataclass
class FetchedSource:
    local_path: str
    original_uri: str
    format_hint: str
    metadata: dict[str, str]
```

---

## Crear un plugin externo

### Paso 1: Crear el paquete

```
mi-plugin-intake/
├── pyproject.toml
└── src/
    └── mi_plugin/
        ├── __init__.py
        └── parser.py
```

### Paso 2: Implementar el protocolo

```python
# src/mi_plugin/parser.py
from __future__ import annotations

from intake.ingest.base import ParsedContent


class AsanaParser:
    """Parser para exports JSON de Asana."""

    def can_parse(self, source: str) -> bool:
        # Detectar si el archivo es un export de Asana
        ...

    def parse(self, source: str) -> ParsedContent:
        # Parsear el archivo y retornar ParsedContent normalizado
        ...
```

Puedes implementar el protocolo V1 (`Parser`) o V2 (`ParserPlugin`). El registry acepta ambos.

### Paso 3: Registrar como entry_point

```toml
# pyproject.toml
[project.entry-points."intake.parsers"]
asana = "mi_plugin.parser:AsanaParser"
```

### Paso 4: Instalar

```bash
pip install mi-plugin-intake
```

El plugin se descubre automaticamente:

```bash
intake plugins list    # "asana" deberia aparecer
intake plugins check   # deberia reportar OK
```

Ahora puedes usar archivos de Asana como fuente:

```bash
intake init "Sprint review" -s asana-export.json
```

---

## Hooks

El `HookManager` permite registrar callbacks que se ejecutan en respuesta a eventos del pipeline:

```python
from intake.plugins.hooks import HookManager

manager = HookManager()

# Registrar un callback
def on_parse_complete(data: dict) -> None:
    print(f"Parsed: {data['source']}")

manager.register("parse_complete", on_parse_complete)

# Emitir un evento
manager.emit("parse_complete", {"source": "reqs.md", "format": "markdown"})
```

### Caracteristicas

- Los callbacks se ejecutan en orden de registro
- Las excepciones se capturan y se logean sin bloquear otros callbacks
- `registered_events` retorna los nombres de eventos con callbacks registrados
- Listo para wiring en fases futuras del pipeline

---

## PluginRegistry API

```python
from intake.plugins.discovery import PluginRegistry

registry = PluginRegistry()

# Descubrir todos los plugins
registry.discover_all()

# Descubrir por grupo
registry.discover_group("intake.parsers")

# Obtener plugins por tipo
parsers = registry.get_parsers()       # dict[str, object]
exporters = registry.get_exporters()   # dict[str, object]
connectors = registry.get_connectors() # dict[str, object]

# Listar informacion de plugins
for info in registry.list_plugins():
    print(f"{info.name} ({info.group}) v{info.version} - V2: {info.is_v2}")

# Verificar compatibilidad
issues = registry.check_compatibility(info)
```

### PluginInfo

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `name` | str | Nombre del plugin |
| `group` | str | Grupo de entry_point |
| `module` | str | Modulo Python |
| `distribution` | str | Paquete que lo provee |
| `version` | str | Version del paquete |
| `is_builtin` | bool | Si es un plugin built-in de intake |
| `is_v2` | bool | Si implementa el protocolo V2 |
| `load_error` | str \| None | Error de carga (si fallo) |

---

## Excepciones

| Excepcion | Descripcion |
|-----------|-------------|
| `PluginError` | Error base de plugins |
| `PluginLoadError` | Fallo al cargar un plugin (import error, modulo no encontrado) |
