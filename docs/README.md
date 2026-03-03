# Documentacion de intake

> De requisitos en cualquier formato a implementacion verificada.

**intake** es una herramienta CLI open-source que transforma requisitos desde multiples fuentes y formatos (Jira, Confluence, PDFs, Markdown, YAML, imagenes, DOCX, texto libre) en una especificacion normalizada y verificable que cualquier agente de IA puede consumir.

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
| [Arquitectura](arquitectura.md) | Arquitectura del sistema, modulos, flujo de datos y decisiones de diseno |
| [Guia CLI](guia-cli.md) | Referencia completa de los 13 comandos/subcomandos con todas sus opciones |
| [Configuracion](configuracion.md) | Todas las opciones de `.intake.yaml`, presets y variables de entorno |
| [Pipeline](pipeline.md) | Como funciona el pipeline de 5 fases en detalle |
| [Formatos de entrada](formatos-entrada.md) | Los 11 parsers soportados, que extraen y como se auto-detectan |
| [Plugins](plugins.md) | Sistema de plugins: protocolos, descubrimiento, hooks y como crear plugins |
| [Verificacion](verificacion.md) | Motor de checks de aceptacion, reporters y CI/CD |
| [Exportacion](exportacion.md) | Formatos de exportacion para agentes IA |
| [Buenas practicas](buenas-practicas.md) | Tips, patrones recomendados y como sacar el maximo provecho |
| [Solucion de problemas](solucion-problemas.md) | Errores comunes, diagnostico y FAQ |

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
intake export specs/pasarela-de-pagos/ -f architect -o output/

# 8. Gestionar plugins
intake plugins list

# 9. Seguimiento de tareas
intake task list specs/pasarela-de-pagos/
intake task update specs/pasarela-de-pagos/ 1 done --note "Implementado"
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
