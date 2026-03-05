# Buenas practicas

Consejos para sacar el maximo provecho de intake.

---

## Escribir buenas fuentes de requisitos

### Se especifico

El LLM extrae mejor los requisitos cuando las fuentes son claras y especificas.

**Bueno:**
```
El sistema debe permitir registro con email y password.
La password debe tener minimo 8 caracteres, una mayuscula y un numero.
El sistema debe enviar un email de confirmacion dentro de 30 segundos.
```

**Malo:**
```
Necesitamos un login bueno y seguro.
```

### Incluye criterios de aceptacion

Los criterios de aceptacion se traducen directamente en checks verificables:

```markdown
## FR-01: Registro de usuarios

El sistema debe permitir registro con email y password.

### Criterios de aceptacion
- Email debe ser unico en el sistema
- Password minimo 8 caracteres
- Se envia email de confirmacion en < 30 segundos
- El endpoint retorna 201 en exito, 409 si el email ya existe
```

### Separa funcional de no funcional

intake distingue entre requisitos funcionales (que hace el sistema) y no funcionales (como lo hace). Separalos en las fuentes para mejor extraccion:

```markdown
# Requisitos funcionales
- El usuario puede registrarse con email
- El usuario puede hacer login con OAuth2

# Requisitos no funcionales
- Tiempo de respuesta < 200ms para todos los endpoints
- El sistema debe soportar 1000 usuarios concurrentes
- Disponibilidad 99.9%
```

---

## Multi-source: combinar formatos

Una de las fortalezas de intake es combinar multiples fuentes. Cada fuente aporta informacion diferente:

```bash
intake init "Mi feature" \
  -s historias-usuario.md \    # Requisitos de negocio (Markdown)
  -s jira-export.json \         # Requisitos tecnicos + estado actual (Jira)
  -s notas-reunion.txt \        # Decisiones informales (texto libre)
  -s wireframes.png             # Diseno visual (imagen)
```

### Que aporta cada formato

| Formato | Mejor para |
|---------|-----------|
| Markdown | Requisitos estructurados, specs formales, documentos de diseno |
| Jira JSON | Estado actual del proyecto, prioridades, links entre issues |
| Texto plano | Notas rapidas, decisiones de reuniones, ideas en bruto |
| YAML | Requisitos ya estructurados con IDs y prioridades |
| Confluence HTML | Documentacion existente, RFCs, decisiones de equipo |
| PDF | Specs externas, documentos regulatorios, contratos |
| DOCX | Documentos de Word de stakeholders |
| Imagenes | Wireframes, mockups, diagramas de arquitectura |
| URLs | Documentacion en wikis, RFCs online, paginas de referencia |
| Slack JSON | Decisiones de equipo, action items, conversaciones tecnicas |
| GitHub Issues | Bugs reportados, feature requests, estado del backlog |

### Deduplicacion automatica

Cuando se combinan fuentes, intake deduplica automaticamente requisitos similares usando similaridad Jaccard (threshold 0.75). Si dos fuentes dicen lo mismo con palabras ligeramente diferentes, solo se conserva la primera ocurrencia.

### Deteccion de conflictos

intake tambien detecta conflictos entre fuentes. Por ejemplo, si un documento dice "usar PostgreSQL" y otro dice "usar MongoDB", se reporta como conflicto con una recomendacion.

---

## Elegir el modo de generacion

intake puede auto-detectar el modo optimo basandose en la complejidad de las fuentes, o puedes forzarlo manualmente:

| Situacion | Modo | Por que |
|-----------|------|---------|
| Bug fix simple, 1 archivo de notas | `quick` | Solo genera context.md + tasks.md, rapido y barato |
| Feature nueva de complejidad normal | `standard` | Los 6 archivos completos |
| Sistema con muchas fuentes o texto extenso | `enterprise` | Maximo detalle y riesgos |
| No estas seguro | (omitir `--mode`) | intake lo auto-detecta |

```bash
# Auto-deteccion (recomendado)
intake init "Mi feature" -s reqs.md

# Forzar modo
intake init "Fix rapido" -s bug.txt --mode quick
intake init "Sistema critico" -s reqs.md -s jira.json -s confluence.html --mode enterprise
```

La auto-deteccion funciona asi:

- **quick**: <500 palabras, 1 fuente, sin contenido estructurado (jira, yaml, etc.)
- **enterprise**: 4+ fuentes O >5000 palabras
- **standard**: todo lo demas

Se puede desactivar la auto-deteccion con `spec.auto_mode: false` en `.intake.yaml`.

---

## Elegir el preset correcto

| Situacion | Preset | Por que |
|-----------|--------|---------|
| Prototipando una idea | `minimal` | Rapido, barato ($0.10), sin extras |
| Proyecto normal de equipo | `standard` | Balance entre detalle y costo ($0.50) |
| Sistema critico / regulado | `enterprise` | Maximo detalle, trazabilidad, riesgos ($2.00) |
| Primera vez usando intake | `standard` | Muestra todas las capacidades |

```bash
intake init "Mi feature" -s reqs.md --preset minimal
```

Tambien puedes empezar con `minimal` y cambiar a `standard` cuando lo necesites:

```bash
# Primer intento rapido
intake init "Mi feature" -s reqs.md --preset minimal

# Version completa
intake init "Mi feature" -s reqs.md --preset standard
```

---

## Gestion de costos

### Entender el costo

Cada `intake init` o `intake add` hace 2-3 llamadas al LLM:

1. **Extraccion** — la mas costosa, procesa todo el texto de las fuentes
2. **Evaluacion de riesgos** — opcional (desactivar con `risk_assessment: false`)
3. **Diseno** — procesa los requisitos extraidos

### Reducir costos

| Estrategia | Como | Ahorro |
|------------|------|--------|
| Usar preset `minimal` | `--preset minimal` | ~80% (desactiva riesgos, lock, sources) |
| Desactivar riesgos | `risk_assessment: false` | ~30% (elimina 1 de 3 llamadas LLM) |
| Usar modelo mas barato | `--model gpt-3.5-turbo` | Variable, depende del modelo |
| Reducir temperatura | `temperature: 0.1` | No reduce costo pero mejora consistencia |
| Budget enforcement | `max_cost_per_spec: 0.25` | Protege contra sorpresas |

### Monitorear costos

```bash
# Ver el costo de una spec generada
intake show specs/mi-feature/
# Muestra: Cost: $0.0423
```

El costo tambien se registra en `spec.lock.yaml`:

```yaml
total_cost: 0.0423
```

---

## Versionado de specs

### Specs como codigo

Las specs generadas son archivos de texto — ideales para versionarlos con git:

```bash
# Generar spec
intake init "Auth system" -s reqs.md

# Commitear
git add specs/auth-system/
git commit -m "Add auth system spec v1"
```

### Comparar versiones

Usa `intake diff` para comparar dos versiones:

```bash
# Despues de regenerar con nuevas fuentes
intake diff specs/auth-system-v1/ specs/auth-system-v2/
```

Muestra requisitos, tareas y checks agregados, eliminados y modificados.

### Detectar cambios en fuentes

El `spec.lock.yaml` tiene hashes de las fuentes. Puedes verificar si las fuentes cambiaron:

```bash
intake show specs/mi-feature/
```

Para integrar la verificacion en CI/CD (GitHub Actions, GitLab CI, Jenkins, Azure DevOps), ver [Integracion CI/CD](integracion-cicd.md).

---

## Seguridad

### Redactar informacion sensible

Si tus fuentes contienen informacion sensible, usa `security.redact_patterns`:

```yaml
security:
  redact_patterns:
    - "sk-[a-zA-Z0-9]{20,}"       # API keys
    - "\\b\\d{4}-\\d{4}-\\d{4}\\b" # Numeros de tarjeta
    - "password:\\s*\\S+"            # Passwords en configs
```

### Excluir archivos sensibles

Por defecto, intake nunca incluye estos archivos en el output:

```yaml
security:
  redact_files:
    - "*.env"
    - "*.pem"
    - "*.key"
```

Agrega mas patrones segun tu proyecto:

```yaml
security:
  redact_files:
    - "*.env"
    - "*.pem"
    - "*.key"
    - "credentials.*"
    - "secrets.*"
```

Para una guia de seguridad completa (modelo de amenazas, modo air-gapped, cumplimiento), ver [Seguridad](seguridad.md).

---

## Organizacion del proyecto

### Estructura recomendada

```
mi-proyecto/
├── .intake.yaml              # Configuracion de intake
├── specs/                    # Specs generadas
│   ├── auth-system/          #   Spec 1
│   │   ├── requirements.md
│   │   ├── design.md
│   │   ├── tasks.md
│   │   ├── acceptance.yaml
│   │   ├── context.md
│   │   ├── sources.md
│   │   └── spec.lock.yaml
│   └── payments/             #   Spec 2
│       └── ...
├── docs/                     # Fuentes de requisitos
│   ├── requirements.md
│   ├── jira-export.json
│   └── meeting-notes.txt
├── src/                      # Codigo fuente
└── tests/                    # Tests
```

Para contenerizacion y despliegue en equipos, ver [Despliegue](despliegue.md).

### Un spec por feature

Genera una spec por cada feature o componente independiente:

```bash
intake init "Auth system" -s docs/auth-reqs.md
intake init "Payments" -s docs/payment-stories.md -s docs/jira-payments.json
intake init "Notifications" -s docs/notif-ideas.txt
```

Esto permite:

- Verificar cada feature independientemente
- Comparar versiones de una feature especifica
- Asignar features a diferentes equipos o agentes

---

## Seguimiento de tareas

Despues de generar una spec, puedes usar `intake task` para seguir el progreso de implementacion directamente en `tasks.md`:

```bash
# Ver el estado de todas las tareas
intake task list specs/mi-feature/

# Marcar una tarea como en progreso
intake task update specs/mi-feature/ 1 in_progress

# Marcar como completada con nota
intake task update specs/mi-feature/ 1 done --note "Tests pasando"

# Filtrar por estado
intake task list specs/mi-feature/ --status pending --status blocked
```

**Estados disponibles:** `pending`, `in_progress`, `done`, `blocked`

El estado se persiste directamente en `tasks.md`, asi que se versiona con git junto con el resto de la spec.

---

## Usar fuentes desde URLs

Puedes pasar URLs directamente como fuentes sin descargar manualmente:

```bash
# Wiki interna
intake init "API review" -s https://wiki.company.com/rfc/auth

# Documentacion publica
intake init "Integration" -s https://docs.example.com/api/v2
```

intake descarga la pagina, convierte el HTML a Markdown, y lo procesa como cualquier otra fuente. Auto-detecta si es contenido de Confluence, Jira, o GitHub por patrones en la URL.

---

## Workflow recomendado

```
1. Recopilar requisitos (cualquier formato, archivos o URLs)
           |
2. intake init "Feature" -s fuente1 -s fuente2
   (opcionalmente: --mode quick|standard|enterprise)
           |
3. Revisar la spec generada
   - requirements.md: requisitos completos?
   - tasks.md: tareas razonables?
   - acceptance.yaml: checks verificables?
           |
4. Iterar si es necesario
   - intake add specs/feature/ -s nueva-fuente.md --regenerate
           |
5. Implementar (manualmente o con agente IA)
   - intake export specs/feature/ -f architect
   - intake task update specs/feature/ 1 in_progress
   - intake watch specs/feature/ -p .  (verificacion continua)
           |
6. Seguir progreso
   - intake task list specs/feature/
   - intake task update specs/feature/ 1 done --note "Implementado"
           |
7. Verificar
   - intake verify specs/feature/ -p .
           |
8. Iterar hasta que todos los checks pasen
```

Para patrones de trabajo por tamano de equipo (individual, equipo, empresa), ver [Flujos de trabajo](flujos-trabajo.md).

---

## Usar el servidor MCP

Si trabajas con agentes IA compatibles con MCP (Claude Code, Claude Desktop, etc.), el servidor MCP de intake permite que el agente acceda directamente a las specs:

```bash
# Iniciar el servidor
intake mcp serve --specs-dir ./specs
```

El agente puede entonces usar tools como `intake_verify`, `intake_get_tasks`, `intake_update_task` sin necesidad de exportar primero. El prompt `implement_next_task` le da al agente el contexto completo para empezar a implementar.

Ver [MCP Server](mcp-server.md) para configuracion y uso.

---

## Verificacion continua con watch

Durante el desarrollo, usa `intake watch` para re-verificar automaticamente cada vez que guardas un archivo:

```bash
intake watch specs/mi-feature/ -p .
```

Esto es especialmente util cuando:

- Estas implementando multiples tareas de una spec
- Quieres feedback inmediato sobre si los checks pasan
- Trabajas en pair programming con un agente IA

Puedes filtrar por tags para solo ejecutar un subconjunto de checks:

```bash
# Solo tests y seguridad
intake watch specs/mi-feature/ -p . -t tests -t security
```

Ver [Watch Mode](watch-mode.md) para configuracion y detalles.
