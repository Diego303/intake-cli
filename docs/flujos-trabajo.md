# Flujos de trabajo

Patrones de uso de intake para diferentes escalas de equipo y organizacion, desde un desarrollador individual hasta empresas multi-equipo con requisitos regulatorios.

---

## Desarrollador individual

### Flujo basico

```
Requisitos → intake init → Revisar spec → Implementar → intake verify → Iterar
```

### Ejemplo end-to-end

```bash
# 1. Recopilar requisitos en un archivo Markdown
echo "# Auth System
- Users register with email and password
- OAuth2 login with Google and GitHub
- JWT tokens with 1h expiry
- Rate limiting: 100 requests/min per user" > reqs.md

# 2. Generar la spec
intake init "Auth system" -s reqs.md

# 3. Revisar la spec generada
intake show specs/auth-system/
# → 4 functional requirements, 6 tasks, 8 acceptance checks

# 4. Exportar para tu agente preferido
intake export specs/auth-system/ -f claude-code -o .

# 5. Implementar (manualmente o con agente)
# ... coding ...

# 6. Verificar cumplimiento
intake verify specs/auth-system/ -p .
# → PASS: 7/8  FAIL: 1/8

# 7. Analizar el fallo
intake feedback specs/auth-system/ -p .
# → MAJOR: Rate limiting not implemented in middleware
#   Fix: Add rate_limit decorator to src/api/routes.py

# 8. Corregir y re-verificar
# ... fix rate limiting ...
intake verify specs/auth-system/ -p .
# → PASS: 8/8

# 9. Marcar tareas como completadas
intake task update specs/auth-system/ 1 done --note "All checks passing"

# 10. Commitear
git add specs/ src/ tests/
git commit -m "feat: implement auth system (spec-verified)"
```

### Quick mode para tareas simples

```bash
# Bug fix rapido: solo genera context.md + tasks.md
intake init "Fix login timeout" -s bug-report.txt --mode quick
```

---

## Equipo pequeno (2-5 desarrolladores)

### Patron: specs compartidas en git

Todo el equipo trabaja con las mismas specs versionadas:

```bash
# Tech lead genera la spec
intake init "Payment gateway" -s jira.json -s confluence.html --preset standard
git add specs/payment-gateway/
git commit -m "spec: add payment gateway requirements"
git push

# Desarrollador clona y trabaja
git pull
intake show specs/payment-gateway/
intake export specs/payment-gateway/ -f cursor -o .
# ... implementar ...
intake verify specs/payment-gateway/ -p .
```

### Patron: spec por feature branch

Cada feature tiene su spec en su propia branch:

```bash
# Branch de feature
git checkout -b feature/notifications

# Generar spec en la branch
intake init "Notification system" -s reqs.md -s slack-decisions.json
git add specs/notification-system/

# Implementar + verificar
# ...

# El PR incluye spec + implementacion
git add src/ tests/ specs/
git commit -m "feat: notification system with spec"
git push origin feature/notifications
# → PR review incluye revision de la spec
```

### Patron: roles de equipo

| Rol | Responsabilidad intake | Comandos principales |
|-----|----------------------|---------------------|
| Tech Lead | Crear y revisar specs | `init`, `add`, `diff`, `show` |
| Developer | Implementar y verificar | `export`, `verify`, `task update` |
| QA | Verificar y reportar | `verify -f junit`, `feedback` |

```bash
# Tech Lead: crear spec desde multiples fuentes
intake init "User dashboard" \
  -s jira://DASH-100,DASH-101,DASH-102 \
  -s confluence://ENG/Dashboard-RFC \
  -s meeting-notes.md \
  --preset standard

# Developer: exportar y trabajar
intake export specs/user-dashboard/ -f claude-code -o .
intake task update specs/user-dashboard/ 1 in_progress

# QA: verificar y generar reporte
intake verify specs/user-dashboard/ -p . -f junit > results.xml
```

---

## Empresa multi-equipo

### Gobernanza de specs

Para organizaciones grandes, las specs necesitan un proceso de aprobacion:

```
1. Product Owner define requisitos (Jira, Confluence, docs)
         ↓
2. Tech Lead genera spec (intake init)
         ↓
3. PR con spec → Review por arquitecto + stakeholders
         ↓
4. Spec aprobada → Merge a main
         ↓
5. Equipo implementa usando spec verificada
         ↓
6. CI ejecuta intake verify en cada PR
         ↓
7. Release solo si todos los checks pasan
```

### Estandarizacion

Compartir configuracion a nivel organizacion:

```yaml
# .intake.yaml en la raiz del monorepo
llm:
  model: claude-sonnet-4
  max_cost_per_spec: 1.00

project:
  language: en
  conventions:
    code_style: "PEP 8"
    testing: "pytest with >80% coverage"
    documentation: "Google-style docstrings"

spec:
  requirements_format: ears
  design_depth: moderate
  task_granularity: medium
  risk_assessment: true
  generate_lock: true

export:
  default_format: claude-code

security:
  redact_patterns:
    - "sk-[a-zA-Z0-9]{20,}"
    - "\\b\\d{4}-\\d{4}-\\d{4}-\\d{4}\\b"
  redact_files:
    - "*.env"
    - "*.pem"
    - "*.key"
    - "credentials.*"
```

**Enforcement:** usar `--preset enterprise` para equipos con requisitos regulatorios.

### Multi-spec para sistemas grandes

Estructura para microservicios o sistemas con multiples componentes:

```
empresa/
├── .intake.yaml                    # Config compartida
├── specs/
│   ├── platform/
│   │   ├── api-gateway/            # Spec del API gateway
│   │   ├── auth-service/           # Spec del servicio de auth
│   │   └── notification-service/   # Spec de notificaciones
│   ├── frontend/
│   │   ├── web-dashboard/          # Spec del dashboard web
│   │   └── mobile-app/             # Spec de la app movil
│   └── infrastructure/
│       ├── monitoring/             # Spec de monitoring
│       └── ci-pipeline/            # Spec del pipeline CI
├── services/
│   ├── api-gateway/
│   ├── auth/
│   └── notifications/
└── frontend/
    ├── web/
    └── mobile/
```

---

## Monorepo multi-spec

### Verificacion por servicio

Cada spec se verifica contra su directorio de proyecto correspondiente:

```bash
# Verificar cada servicio contra su spec
intake verify specs/platform/api-gateway/ -p services/api-gateway/
intake verify specs/platform/auth-service/ -p services/auth/
intake verify specs/frontend/web-dashboard/ -p frontend/web/
```

### CI matrix para paralelo

```yaml
# GitHub Actions
jobs:
  verify:
    strategy:
      matrix:
        include:
          - spec: specs/platform/api-gateway
            project: services/api-gateway
          - spec: specs/platform/auth-service
            project: services/auth
          - spec: specs/frontend/web-dashboard
            project: frontend/web
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - run: pip install intake-ai-cli
      - run: intake verify ${{ matrix.spec }}/ -p ${{ matrix.project }}/ -f junit > results.xml
```

---

## Ciclo de vida de una spec

### Crear → Verificar → Actualizar → Deprecar

```bash
# CREAR: nueva spec
intake init "Payment v2" -s reqs.md -s jira.json

# VERIFICAR: en cada push/PR
intake verify specs/payment-v2/ -p .

# ACTUALIZAR: cuando los requisitos cambian
intake add specs/payment-v2/ -s nuevos-reqs.md --regenerate

# COMPARAR: que cambio entre versiones
intake diff specs/payment-v1/ specs/payment-v2/

# DEPRECAR: archivar specs obsoletas
mkdir -p specs/archived
mv specs/payment-v1/ specs/archived/
git add specs/ && git commit -m "archive: payment v1 (replaced by v2)"
```

### Gestion de cambios

Cuando los requisitos cambian:

```bash
# 1. Regenerar spec con nueva fuente
intake add specs/mi-feature/ -s updated-reqs.md --regenerate

# 2. Comparar con la version anterior
intake diff specs/mi-feature-backup/ specs/mi-feature/
# → Added: FR-005 (new requirement)
# → Modified: FR-002 (scope changed)
# → Removed: FR-003 (no longer needed)

# 3. Revisar los cambios
intake show specs/mi-feature/

# 4. Re-verificar la implementacion
intake verify specs/mi-feature/ -p .

# 5. Si hay fallos, analizar
intake feedback specs/mi-feature/ -p .
```

---

## Workflow con agentes IA

### Ciclo completo

```
intake init → intake export → Agente implementa → intake verify → intake feedback → Agente corrige → Repeat
```

```bash
# 1. Generar spec
intake init "Feature X" -s reqs.md

# 2. Exportar para el agente
intake export specs/feature-x/ -f claude-code -o .

# 3. El agente lee CLAUDE.md + .intake/tasks/ e implementa

# 4. Verificar
intake verify specs/feature-x/ -p .

# 5. Si hay fallos, generar feedback
intake feedback specs/feature-x/ -p . --agent-format claude-code
# → El agente lee las sugerencias y corrige

# 6. Re-verificar hasta que todo pase
intake verify specs/feature-x/ -p .
# → PASS: 12/12

# 7. Marcar tareas
intake task update specs/feature-x/ 1 done
```

### Formato de exportacion por agente

| Agente | Formato | Que lee el agente | Comando |
|--------|---------|-------------------|---------|
| Claude Code | `claude-code` | `CLAUDE.md` + `.intake/tasks/TASK-NNN.md` | `intake export -f claude-code -o .` |
| Cursor | `cursor` | `.cursor/rules/intake-spec.mdc` | `intake export -f cursor -o .` |
| Kiro | `kiro` | `requirements.md` + `design.md` + `tasks.md` (formato nativo) | `intake export -f kiro -o .` |
| GitHub Copilot | `copilot` | `.github/copilot-instructions.md` | `intake export -f copilot -o .` |
| Architect | `architect` | `pipeline.yaml` con steps | `intake export -f architect -o output/` |
| Cualquiera | `generic` | `SPEC.md` consolidado + `verify.sh` | `intake export -f generic -o output/` |

### Feedback formateado por agente

```bash
# Sugerencias para Claude Code
intake feedback specs/feature-x/ -p . --agent-format claude-code

# Sugerencias para Cursor
intake feedback specs/feature-x/ -p . --agent-format cursor

# Sugerencias genericas (Markdown)
intake feedback specs/feature-x/ -p . --agent-format generic
```

---

## Industrias reguladas

### Audit trail completo

Para industrias que requieren trazabilidad (finanzas, salud, gobierno):

```yaml
# .intake.yaml — configuracion para maxima trazabilidad
spec:
  requirements_format: ears        # Formato formal
  include_sources: true            # Trazabilidad requisito-fuente
  generate_lock: true              # Artefacto de auditoria
  risk_assessment: true            # Evaluacion de riesgos
  auto_mode: false                 # Siempre modo completo

export:
  default_format: generic          # SPEC.md consolidado como documento formal
```

```bash
# Generar con preset enterprise
intake init "Regulated Feature" -s reqs.md --preset enterprise

# El resultado incluye:
# - requirements.md    → requisitos formales con IDs
# - sources.md         → trazabilidad a fuentes originales
# - spec.lock.yaml     → hashes, timestamps, costos
# - acceptance.yaml    → checks verificables
```

### Gates de aprobacion

```
Fase 1: Especificacion
  ├── Product Owner define requisitos
  ├── intake init genera spec
  ├── PR: spec review por arquitecto + compliance
  └── Merge (gate: aprobacion del arquitecto)

Fase 2: Implementacion
  ├── Developer exporta spec para agente
  ├── Implementacion
  ├── CI ejecuta intake verify
  └── PR (gate: todos los checks pasan)

Fase 3: Release
  ├── QA ejecuta intake verify -f junit
  ├── Reporte JUnit como evidencia
  ├── intake show para metricas
  └── Release (gate: aprobacion QA + compliance)
```

### Trazabilidad bidireccional

intake proporciona la cadena completa de trazabilidad:

```
Fuente (reqs.md, jira.json)
    ↓ registrado en sources.md
Requisito (FR-001 en requirements.md)
    ↓ referenciado en design.md
Componente (AuthService)
    ↓ asignado en tasks.md
Tarea (Task 1: Implement AuthService)
    ↓ verificado en acceptance.yaml
Check (check-01: Tests pasan)
    ↓ evidencia en verify report (JUnit XML)
Resultado verificable
```

Cada eslabón es un archivo de texto versionable, auditable y consultable.

Ver [Seguridad > Auditoria y trazabilidad](seguridad.md#auditoria-y-trazabilidad) para mas detalles.
