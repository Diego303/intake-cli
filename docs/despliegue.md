# Despliegue

Guia para desplegar intake en entornos de equipo, contenedores y pipelines de CI.

---

## Instalacion en equipos

### Instalacion estandar

```bash
pip install intake-ai-cli
```

Con conectores API (Jira, Confluence, GitHub, GitLab):

```bash
pip install "intake-ai-cli[connectors]"
```

### Instalacion en virtualenv dedicado

Recomendado para aislar intake del Python del sistema:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install intake-ai-cli
```

### Fijar version para equipos

En un `requirements.txt` o `pyproject.toml` del proyecto:

```text
# requirements-tools.txt
intake-ai-cli==0.6.0
```

```bash
pip install -r requirements-tools.txt
```

Esto garantiza que todo el equipo usa la misma version de intake.

---

## Docker

### Dockerfile

Dockerfile multi-stage optimizado para produccion:

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir --prefix=/install intake-ai-cli

# Stage 2: Runtime
FROM python:3.12-slim

COPY --from=builder /install /usr/local

# intake no necesita root
RUN useradd --create-home intake
USER intake
WORKDIR /workspace

ENTRYPOINT ["intake"]
```

Con conectores:

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir --prefix=/install "intake-ai-cli[connectors]"

FROM python:3.12-slim
COPY --from=builder /install /usr/local
RUN useradd --create-home intake
USER intake
WORKDIR /workspace
ENTRYPOINT ["intake"]
```

### Uso con Docker

```bash
# Construir la imagen
docker build -t intake .

# Generar una spec (montar fuentes y output)
docker run --rm \
  -v $(pwd):/workspace \
  -e ANTHROPIC_API_KEY \
  intake init "Mi feature" -s /workspace/reqs.md

# Verificar una spec (no necesita API key)
docker run --rm \
  -v $(pwd):/workspace \
  intake verify /workspace/specs/mi-feature/ -p /workspace

# Exportar para Claude Code
docker run --rm \
  -v $(pwd):/workspace \
  intake export /workspace/specs/mi-feature/ -f claude-code -o /workspace

# Doctor check
docker run --rm intake doctor
```

**Importante:** Las API keys se pasan via `-e`, nunca se incluyen en la imagen.

### docker-compose.yml

Para equipos que prefieren docker-compose:

```yaml
services:
  intake:
    build: .
    volumes:
      - .:/workspace
    env_file:
      - .env
    working_dir: /workspace
```

```bash
# Generar spec
docker compose run --rm intake init "Feature" -s reqs.md

# Verificar
docker compose run --rm intake verify specs/feature/ -p .

# Exportar
docker compose run --rm intake export specs/feature/ -f cursor -o .

# Feedback
docker compose run --rm intake feedback specs/feature/ -p .
```

### .env para Docker

```bash
# .env (no commitear)
ANTHROPIC_API_KEY=sk-ant-api03-tu-key
JIRA_API_TOKEN=tu-token
JIRA_EMAIL=dev@company.com
GITHUB_TOKEN=ghp_tu-token
GITLAB_TOKEN=glpat-tu-token
```

```bash
# .env.example (commitear como referencia)
ANTHROPIC_API_KEY=
JIRA_API_TOKEN=
JIRA_EMAIL=
GITHUB_TOKEN=
GITLAB_TOKEN=
```

### .dockerignore

```
.git
.venv
__pycache__
*.pyc
.env
.env.*
*.pem
*.key
node_modules
.mypy_cache
.pytest_cache
```

---

## Pre-commit hooks

### intake verify como hook

Ejecutar verificacion automaticamente en cada commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: intake-verify
        name: Verify spec compliance
        entry: intake verify specs/mi-feature/ -p . --fail-fast
        language: system
        pass_filenames: false
        stages: [pre-commit]
        # Solo ejecutar si cambio codigo fuente
        files: ^src/
```

### intake doctor como hook

Check ligero del entorno en cada commit:

```yaml
  - repo: local
    hooks:
      - id: intake-doctor
        name: Check intake environment
        entry: intake doctor
        language: system
        pass_filenames: false
        stages: [pre-commit]
        always_run: true
```

### Instalacion de pre-commit

```bash
pip install pre-commit
pre-commit install
```

**Nota:** Los checks de tipo `command` en `acceptance.yaml` pueden ser lentos (tests, lint). Usa `--tags` para ejecutar solo checks rapidos en pre-commit:

```yaml
entry: intake verify specs/mi-feature/ -p . --fail-fast -t structure -t security
```

---

## Patrones de despliegue

### Como paso en CI pipelines

El caso de uso mas comun: verificar specs en cada PR y exportar al mergear.

```
PR abierto → intake verify (CI) → Review → Merge → intake export (CI)
```

Ver [Integracion CI/CD](integracion-cicd.md) para ejemplos completos de GitHub Actions, GitLab CI, Jenkins y Azure DevOps.

### Como job programado (spec drift)

Detectar cuando las fuentes cambian y la spec queda desactualizada:

```bash
# Cron job semanal: verificar si las fuentes cambiaron
# (spec.lock.yaml tiene hashes de las fuentes)
intake show specs/mi-feature/
# Si staleness detected → crear issue / notificar
```

Ver [Integracion CI/CD > Deteccion de spec drift](integracion-cicd.md#deteccion-de-spec-drift) para la implementacion.

### En pipeline de agentes IA

```
1. intake init (generar spec)
2. intake export -f claude-code (exportar para agente)
3. Agente implementa
4. intake verify (verificar cumplimiento)
5. intake feedback (analizar fallos)
6. Agente corrige
7. Repetir 4-6 hasta que todos los checks pasen
```

Ver [Flujos de trabajo > Workflow con agentes IA](flujos-trabajo.md#workflow-con-agentes-ia) para detalles.

---

## Variables de entorno por caso de uso

| Caso de uso | Variables necesarias |
|------------|---------------------|
| `intake verify` | Ninguna |
| `intake export` | Ninguna |
| `intake show/list/diff` | Ninguna |
| `intake doctor` | Ninguna |
| `intake task` | Ninguna |
| `intake init/add` | `ANTHROPIC_API_KEY` (o la del proveedor LLM configurado) |
| `intake feedback` | `ANTHROPIC_API_KEY` (o la del proveedor LLM) |
| Conector Jira | `JIRA_API_TOKEN` + `JIRA_EMAIL` |
| Conector Confluence | `CONFLUENCE_API_TOKEN` + `CONFLUENCE_EMAIL` |
| Conector GitHub | `GITHUB_TOKEN` |
| Conector GitLab | `GITLAB_TOKEN` |

**Nota:** Los nombres de las variables son configurables en `.intake.yaml`. Los valores por defecto se listan arriba.

Ver [Seguridad](seguridad.md) para mejores practicas de gestion de secretos.

---

## Requisitos de sistema

| Recurso | Minimo | Recomendado |
|---------|--------|-------------|
| Python | 3.12+ | 3.12+ |
| RAM | 256 MB | 512 MB |
| Disco | 50 MB (instalacion) | 100 MB (con conectores) |
| Red | Solo para init/add/feedback/connectors | — |
| CPU | 1 core | 2+ cores (para checks paralelos en verify) |

intake es una herramienta ligera. El recurso mas costoso es la llamada al LLM, que depende del proveedor externo.
