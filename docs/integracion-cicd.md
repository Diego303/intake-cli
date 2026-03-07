# Integracion CI/CD

Guia completa para integrar intake en pipelines de integracion continua. Incluye ejemplos para GitHub Actions, GitLab CI, Jenkins y Azure DevOps.

---

## Estrategia general

### Que ejecutar en CI

| Accion | Cuando | Comando |
|--------|--------|---------|
| Verificar spec | En cada PR / push | `intake verify specs/<spec>/ -p . -f junit` |
| Validar spec | En cada PR / push | `intake validate specs/<spec>/` |
| Exportar spec | Al mergear a main | `intake export specs/<spec>/ -f <formato> -o .` |
| Generar CI config | Una vez / setup | `intake export-ci specs/<spec>/ -p github` o `-p gitlab` |
| Detectar drift | Programado (semanal) | Comparar hashes de `spec.lock.yaml` con fuentes |
| Doctor check | Programado / manual | `intake doctor` |
| Feedback | Cuando verify falla | `intake feedback specs/<spec>/ -p .` |

### Exit codes

| Codigo | Significado | Accion CI |
|--------|-------------|-----------|
| `0` | Todos los checks requeridos pasaron | Job pasa |
| `1` | Al menos un check requerido fallo | Job falla |
| `2` | Error de ejecucion | Job falla (investigar) |

---

## GitHub Actions

### Action oficial de intake (recomendado)

intake incluye una **GitHub Action oficial** (`action/action.yml`) que simplifica la integracion. La action instala intake, ejecuta verificacion, genera reportes y sube artefactos automaticamente.

```yaml
name: Verify Spec
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verify spec compliance
        uses: Diego303/intake-cli/action@main
        with:
          spec-dir: specs/mi-feature/
```

#### Inputs

| Input | Default | Descripcion |
|-------|---------|-------------|
| `spec-dir` | *(requerido)* | Path al directorio de la spec |
| `project-dir` | `.` | Directorio del proyecto contra el cual verificar |
| `report-format` | `junit` | Formato del reporte: `terminal`, `json`, `junit` |
| `report-output` | `intake-verify-report.xml` | Path del archivo de reporte |
| `tags` | `""` | Tags para filtrar checks (separados por coma) |
| `fail-fast` | `false` | Detener en el primer fallo |
| `python-version` | `3.12` | Version de Python |
| `intake-version` | `latest` | Version de intake (ej: `>=0.4.0`) |

#### Outputs

| Output | Descripcion |
|--------|-------------|
| `result` | Resultado: `pass`, `fail`, o `error` |
| `total-checks` | Total de checks ejecutados |
| `passed-checks` | Checks que pasaron |
| `failed-checks` | Checks que fallaron |
| `report-path` | Path al reporte generado |

#### Ejemplo avanzado con outputs

```yaml
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verify spec compliance
        id: verify
        uses: Diego303/intake-cli/action@main
        with:
          spec-dir: specs/mi-feature/
          tags: "api,security"
          fail-fast: "true"

      - name: Comment on PR
        if: failure()
        run: |
          echo "Spec verification failed: ${{ steps.verify.outputs.failed-checks }} checks failed"
```

### Verificacion manual en PR

Si prefieres configurar los steps manualmente sin la action oficial:

```yaml
name: Verify Spec Compliance
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-intake

      - name: Install intake
        run: pip install intake-ai-cli

      - name: Run acceptance checks
        run: intake verify specs/mi-feature/ -p . -f junit > test-results.xml

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: spec-verification
          path: test-results.xml

      - name: Publish test results
        uses: dorny/test-reporter@v1
        if: always()
        with:
          name: Spec Compliance
          path: test-results.xml
          reporter: java-junit
```

### Workflow completo: verificar + exportar

```yaml
name: Spec Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install intake-ai-cli
      - run: intake verify specs/mi-feature/ -p . -f junit > test-results.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: test-results.xml

  export:
    needs: verify
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install intake-ai-cli
      - run: intake export specs/mi-feature/ -f claude-code -o .
      - uses: actions/upload-artifact@v4
        with:
          name: exported-spec
          path: |
            CLAUDE.md
            .intake/
```

### Deteccion de spec drift (scheduled)

```yaml
name: Spec Drift Detection
on:
  schedule:
    - cron: "0 9 * * 1"  # Lunes a las 9am

jobs:
  check-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install intake-ai-cli

      - name: Check for stale specs
        id: drift
        run: |
          OUTPUT=$(intake show specs/mi-feature/ 2>&1)
          if echo "$OUTPUT" | grep -qi "stale\|changed"; then
            echo "drift=true" >> $GITHUB_OUTPUT
          else
            echo "drift=false" >> $GITHUB_OUTPUT
          fi

      - name: Create issue if drift detected
        if: steps.drift.outputs.drift == 'true'
        run: |
          gh issue create \
            --title "Spec drift detected: mi-feature" \
            --body "Las fuentes de la spec han cambiado. Regenerar con: \`intake add specs/mi-feature/ --regenerate\`" \
            --label "spec-drift"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Multiples specs en paralelo

```yaml
jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        spec: [api-auth, api-payments, frontend-dashboard]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install intake-ai-cli
      - run: intake verify specs/${{ matrix.spec }}/ -p . -f junit > results-${{ matrix.spec }}.xml
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: results-${{ matrix.spec }}
          path: results-${{ matrix.spec }}.xml
```

---

## GitLab CI

### Pipeline basico

```yaml
# .gitlab-ci.yml
stages:
  - verify

verify-spec:
  stage: verify
  image: python:3.12-slim
  before_script:
    - pip install intake-ai-cli
  script:
    - intake verify specs/mi-feature/ -p . -f junit > test-results.xml
  artifacts:
    when: always
    reports:
      junit: test-results.xml
```

GitLab muestra automaticamente los resultados JUnit en el widget de Merge Request.

### Pipeline completo con cache

```yaml
stages:
  - verify
  - export

.intake-base:
  image: python:3.12-slim
  cache:
    key: intake-pip
    paths:
      - .cache/pip
  variables:
    PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"
  before_script:
    - pip install intake-ai-cli

verify-spec:
  extends: .intake-base
  stage: verify
  script:
    - intake verify specs/mi-feature/ -p . -f junit > test-results.xml
  artifacts:
    when: always
    reports:
      junit: test-results.xml

export-spec:
  extends: .intake-base
  stage: export
  only:
    - main
  script:
    - intake export specs/mi-feature/ -f claude-code -o .
  artifacts:
    paths:
      - CLAUDE.md
      - .intake/
```

---

## Jenkins

### Jenkinsfile declarativo

```groovy
pipeline {
    agent {
        docker {
            image 'python:3.12-slim'
        }
    }

    environment {
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
    }

    stages {
        stage('Install') {
            steps {
                sh 'pip install intake-ai-cli'
            }
        }

        stage('Verify') {
            steps {
                sh 'intake verify specs/mi-feature/ -p . -f junit > test-results.xml'
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('Export') {
            when {
                branch 'main'
            }
            steps {
                sh 'intake export specs/mi-feature/ -f claude-code -o .'
                archiveArtifacts artifacts: 'CLAUDE.md,.intake/**'
            }
        }
    }
}
```

### Jenkinsfile con multiples specs

```groovy
pipeline {
    agent any
    stages {
        stage('Verify All Specs') {
            parallel {
                stage('API Auth') {
                    steps {
                        sh 'intake verify specs/api-auth/ -p . -f junit > results-auth.xml'
                    }
                }
                stage('API Payments') {
                    steps {
                        sh 'intake verify specs/api-payments/ -p . -f junit > results-payments.xml'
                    }
                }
            }
            post {
                always {
                    junit 'results-*.xml'
                }
            }
        }
    }
}
```

---

## Azure DevOps

### azure-pipelines.yml

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.12'

  - script: pip install intake-ai-cli
    displayName: 'Install intake'

  - script: intake verify specs/mi-feature/ -p . -f junit > test-results.xml
    displayName: 'Verify spec compliance'

  - task: PublishTestResults@2
    condition: always()
    inputs:
      testResultsFormat: 'JUnit'
      testResultsFiles: 'test-results.xml'
      testRunTitle: 'Spec Compliance'
```

---

## Formatos de reporte para CI

### JUnit XML

El formato mas compatible con CI. Todos los sistemas lo soportan:

```bash
intake verify specs/mi-feature/ -p . -f junit > test-results.xml
```

| Plataforma | Como se consume |
|-----------|----------------|
| GitHub Actions | `dorny/test-reporter` action o `actions/upload-artifact` |
| GitLab CI | `artifacts.reports.junit` (aparece en MR widget) |
| Jenkins | `junit` post step (aparece en dashboard) |
| Azure DevOps | `PublishTestResults@2` task |

### JSON

Para integraciones personalizadas:

```bash
intake verify specs/mi-feature/ -p . -f json > results.json
```

Extraer metricas con `jq`:

```bash
# Total de checks
jq '.total_checks' results.json

# Solo nombres de checks fallidos
jq '.results[] | select(.passed == false) | .name' results.json

# Resumen: passed/failed
jq '{passed: .passed, failed: .failed, all_ok: .all_required_passed}' results.json
```

---

## Pre-commit hooks

Ver [Despliegue > Pre-commit hooks](despliegue.md#pre-commit-hooks) para configuracion detallada.

Resumen rapido:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: intake-verify
        name: Verify spec compliance
        entry: intake verify specs/mi-feature/ -p . --fail-fast -t structure
        language: system
        pass_filenames: false
        files: ^src/
```

---

## Deteccion de spec drift

### Que es

"Spec drift" ocurre cuando las fuentes de requisitos cambian pero la spec no se regenera. El `spec.lock.yaml` almacena hashes SHA-256 de las fuentes originales, permitiendo detectar cambios.

### Cuando verificar

- **Semanal** (cron job): detectar drift por fuentes que cambian sin regenerar
- **En PR**: si un PR modifica una fuente listada en `spec.lock.yaml`, alertar que la spec puede estar desactualizada

### Implementacion

El patron general:

```bash
# 1. intake show detecta staleness automaticamente
intake show specs/mi-feature/

# 2. Si las fuentes cambiaron, regenerar
intake add specs/mi-feature/ --regenerate

# 3. Revisar cambios
intake diff specs/mi-feature-old/ specs/mi-feature/
```

Ver los ejemplos de GitHub Actions y GitLab CI arriba para implementaciones en CI.

---

## Notificaciones

### Slack (webhook)

```yaml
# GitHub Actions: notificar en Slack si verify falla
- name: Notify Slack on failure
  if: failure()
  run: |
    curl -X POST "${{ secrets.SLACK_WEBHOOK }}" \
      -H "Content-Type: application/json" \
      -d '{
        "text": "Spec verification failed for mi-feature",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Spec Verification Failed*\nSpec: `mi-feature`\nBranch: `${{ github.ref_name }}`\nPR: ${{ github.event.pull_request.html_url }}"
            }
          }
        ]
      }'
```

### Microsoft Teams (webhook)

```yaml
- name: Notify Teams on failure
  if: failure()
  run: |
    curl -X POST "${{ secrets.TEAMS_WEBHOOK }}" \
      -H "Content-Type: application/json" \
      -d '{
        "title": "Spec Verification Failed",
        "text": "La spec mi-feature no paso los checks de aceptacion en la branch ${{ github.ref_name }}"
      }'
```

---

## Generacion automatica de CI config

intake puede generar automaticamente archivos de configuracion CI para verificacion de specs. Esto simplifica el setup inicial:

```bash
# Generar GitLab CI config
intake export-ci specs/mi-feature/ -p gitlab
# Genera: .gitlab-ci.yml

# Generar GitHub Actions workflow
intake export-ci specs/mi-feature/ -p github
# Genera: .github/workflows/intake-verify.yml

# Generar en directorio personalizado
intake export-ci specs/mi-feature/ -p github -o ci-config/
```

Los archivos generados incluyen instalacion de intake, ejecucion de `intake verify`, y reporte JUnit. Se pueden personalizar despues de generarlos.

**Nota:** `export-ci` usa templates Jinja2 built-in (`gitlab_ci.yml.j2`, `github_actions.yml.j2`). Si necesitas customizarlos, puedes sobreescribirlos con [templates de usuario](configuracion.md#seccion-templates).

---

## Tips

### Cache de dependencias

Cachear pip reduce ~30 segundos por ejecucion:

```yaml
# GitHub Actions
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-intake-${{ hashFiles('**/requirements*.txt') }}

# GitLab CI
cache:
  key: intake-pip
  paths:
    - .cache/pip
```

### verify.sh sin instalar intake

El exporter `generic` genera un `verify.sh` standalone. En CI donde no quieres instalar intake:

```bash
# Una vez: generar verify.sh y commitearlo
intake export specs/mi-feature/ -f generic -o output/
git add output/verify.sh
git commit -m "Add standalone verify script"

# En CI: ejecutar directamente (sin intake)
chmod +x output/verify.sh
./output/verify.sh .
```

**Tradeoff:** menos flexible que `intake verify` (sin tags, sin JUnit), pero zero dependencias.

### Verificacion solo de estructura

Para checks rapidos en pre-commit, ejecutar solo checks de estructura (sin tests):

```bash
intake verify specs/mi-feature/ -p . -t structure --fail-fast
```
