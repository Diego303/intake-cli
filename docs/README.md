# Documentacion de intake

> De requisitos en cualquier formato a implementacion verificada.

**intake** es una herramienta CLI open-source que transforma requisitos desde multiples fuentes y formatos (Jira, Confluence, GitHub, GitLab, PDFs, Markdown, YAML, imagenes, DOCX, texto libre) en una especificacion normalizada y verificable que cualquier agente de IA puede consumir.

```
intake = Requisitos caoticos (N fuentes, N formatos) -> Spec ejecutable -> Cualquier agente IA
```

---

## Requisitos previos

- **Python 3.12+**
- **API key de un proveedor LLM** (Anthropic, OpenAI, Google, etc.)

## Instalacion

```bash
pip install intake-ai-cli
```

El comando CLI se llama `intake`:

```bash
intake --version
intake doctor
```

Para desarrollo local:

```bash
git clone https://github.com/your-org/intake-cli.git
cd intake-cli
pip install -e ".[dev]"
```

---

## Guias

| Documento | Descripcion |
|-----------|-------------|
**Core:**

| Documento | Descripcion |
|-----------|-------------|
| [Arquitectura](arquitectura.md) | Arquitectura del sistema, modulos, flujo de datos y decisiones de diseno |
| [Guia CLI](guia-cli.md) | Referencia completa de los 22 comandos/subcomandos con todas sus opciones |
| [Configuracion](configuracion.md) | Todas las opciones de `.intake.yaml`, presets y variables de entorno |

**Pipeline:**

| Documento | Descripcion |
|-----------|-------------|
| [Pipeline](pipeline.md) | Como funciona el pipeline de 5 fases + feedback loop en detalle |
| [Formatos de entrada](formatos-entrada.md) | Los 12 parsers + 4 conectores API, que extraen y como se auto-detectan |
| [Conectores](conectores.md) | Conectores API directos: Jira, Confluence, GitHub, GitLab |
| [Plugins](plugins.md) | Sistema de plugins: protocolos, descubrimiento, hooks y como crear plugins |
| [Verificacion](verificacion.md) | Motor de checks de aceptacion, reporters y CI/CD |
| [Exportacion](exportacion.md) | 6 formatos de exportacion para agentes IA |
| [Feedback](feedback.md) | Feedback loop: analisis de fallos y enmiendas a la spec |
| [MCP Server](mcp-server.md) | Servidor MCP para agentes IA: tools, resources, prompts y transportes |
| [Watch Mode](watch-mode.md) | Modo watch: monitoreo de archivos y re-verificacion automatica |

**Operaciones y enterprise:**

| Documento | Descripcion |
|-----------|-------------|
| [Despliegue](despliegue.md) | Docker, pre-commit hooks y patrones de despliegue para equipos |
| [Integracion CI/CD](integracion-cicd.md) | GitHub Actions, GitLab CI, Jenkins, Azure DevOps |
| [Seguridad](seguridad.md) | Modelo de amenazas, gestion de secretos, redaccion, cumplimiento |
| [Flujos de trabajo](flujos-trabajo.md) | Patrones para equipos de todos los tamanos: individual a empresa |

**Referencia:**

| Documento | Descripcion |
|-----------|-------------|
| [Buenas practicas](buenas-practicas.md) | Tips, patrones recomendados y como sacar el maximo provecho |
| [Templates personalizados](templates-personalizados.md) | Personalizar templates Jinja2: variables, overrides y ejemplos |
| [Solucion de problemas](solucion-problemas.md) | Errores comunes, diagnostico y FAQ |

**Release notes:**

| Documento | Descripcion |
|-----------|-------------|
| [v0.6.0](github-notes/v0.6.0.md) | GitLab connector + parser, validate, estimate, custom templates, CI export |
| [v0.5.0](github-notes/v0.5.0.md) | Polish, CI/CD, GitHub Actions action, mypy --strict, 5 examples |
| [v0.4.0](github-notes/v0.4.0.md) | MCP server + Watch mode |
| [v0.3.0](github-notes/v0.3.0.md) | Connectors + Exporters + Feedback loop |
| [v0.2.0](github-notes/v0.2.0.md) | Plugin system + New parsers + Adaptive generation |
| [v0.1.0](github-notes/v0.1.0.md) | Initial release |

---

## Inicio rapido

```bash
# 1. Verificar que el entorno esta listo
intake doctor

# 2. Generar una spec desde un archivo Markdown
intake init "Sistema de autenticacion OAuth2" -s requirements.md

# 3. Generar desde multiples fuentes
intake init "Pasarela de pagos" -s jira.json -s confluence.html -s notas.md

# 4. Modo rapido para tareas simples (solo context.md + tasks.md)
intake init "Fix login bug" -s notas.txt --mode quick

# 5. Desde una URL
intake init "API review" -s https://wiki.company.com/rfc/auth

# 6. Verificar la implementacion contra la spec
intake verify specs/pasarela-de-pagos/ -p .

# 7. Exportar para un agente especifico
intake export specs/pasarela-de-pagos/ -f claude-code -o .
intake export specs/pasarela-de-pagos/ -f cursor -o .
intake export specs/pasarela-de-pagos/ -f copilot -o .

# 8. Desde conectores API directos (requiere config)
intake init "Sprint tasks" -s jira://PROJ/sprint/42
intake init "RFC review" -s confluence://ENG/Architecture-RFC
intake init "Sprint review" -s gitlab://team/backend/issues?labels=sprint

# 9. Feedback loop: analizar fallos y sugerir correcciones
intake feedback specs/pasarela-de-pagos/ -p .

# 10. Gestionar plugins
intake plugins list

# 11. Seguimiento de tareas
intake task list specs/pasarela-de-pagos/
intake task update specs/pasarela-de-pagos/ 1 done --note "Implementado"

# 12. Servidor MCP para agentes IA
intake mcp serve --transport stdio

# 13. Watch mode: re-verificar al cambiar archivos
intake watch specs/pasarela-de-pagos/ --project-dir . --verbose

# 14. Validar consistencia interna de una spec
intake validate specs/pasarela-de-pagos/

# 15. Estimar costo antes de generar
intake estimate -s requirements.md -s notas.md

# 16. Generar CI config para verificacion
intake export-ci specs/pasarela-de-pagos/ -p gitlab
```

---

## Los 6 archivos spec

Cada spec generada contiene:

| Archivo | Proposito |
|---------|-----------|
| `requirements.md` | Que construir. Requisitos funcionales y no funcionales. |
| `design.md` | Como construirlo. Arquitectura, interfaces, decisiones tecnicas. |
| `tasks.md` | En que orden. Tareas atomicas con dependencias. |
| `acceptance.yaml` | Como verificar. Checks ejecutables: comandos, patrones, archivos. |
| `context.md` | Contexto del proyecto para el agente: stack, convenciones, estado. |
| `sources.md` | Trazabilidad completa: cada requisito mapeado a su fuente original. |

Ademas se genera `spec.lock.yaml` para reproducibilidad (hashes de fuentes, costos, timestamps).
