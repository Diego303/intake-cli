# Verificacion

El motor de verificacion ejecuta checks de aceptacion definidos en `acceptance.yaml` contra el directorio del proyecto. Responde la pregunta: "la implementacion cumple con la spec?"

---

## Comando

```bash
intake verify <SPEC_DIR> -p <PROJECT_DIR> [opciones]
```

```bash
# Verificar con reporte en terminal
intake verify specs/api-de-usuarios/ -p .

# Solo checks con tag "api"
intake verify specs/api-de-usuarios/ -p . -t api -t security

# Formato JUnit para CI
intake verify specs/api-de-usuarios/ -p . -f junit > test-results.xml

# Detenerse en el primer fallo
intake verify specs/api-de-usuarios/ -p . --fail-fast
```

---

## Estructura de acceptance.yaml

```yaml
checks:
  - id: check-01
    name: "Tests unitarios pasan"
    type: command
    command: "python -m pytest tests/ -q"
    required: true
    tags: [tests, ci]

  - id: check-02
    name: "Archivo de rutas existe"
    type: files_exist
    paths:
      - src/routes.py
      - src/models.py
    required: true
    tags: [structure]

  - id: check-03
    name: "Endpoints tienen autenticacion"
    type: pattern_present
    glob: "src/**/*.py"
    patterns:
      - "auth_required|@login_required|verify_token"
    required: true
    tags: [security]

  - id: check-04
    name: "Sin passwords hardcodeados"
    type: pattern_absent
    glob: "src/**/*.py"
    patterns:
      - "password\\s*=\\s*['\"]\\w+"
    required: true
    tags: [security]
```

---

## Los 4 tipos de check

### command

Ejecuta un comando shell y verifica que el exit code sea 0.

```yaml
- id: check-tests
  name: "Tests pasan"
  type: command
  command: "python -m pytest tests/ -q"
  required: true
```

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `command` | string | Comando shell a ejecutar |

El comando se ejecuta en el directorio del proyecto (`--project-dir`). Se captura stdout y stderr (truncados a 1000 y 500 chars respectivamente).

**Timeout:** configurable via `verification.timeout_per_check` (default: 120 segundos).

### files_exist

Verifica que todos los archivos listados existen.

```yaml
- id: check-structure
  name: "Archivos principales existen"
  type: files_exist
  paths:
    - src/main.py
    - src/models.py
    - tests/test_main.py
  required: true
```

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `paths` | list[string] | Paths relativos al directorio del proyecto |

Falla si **cualquiera** de los paths no existe.

### pattern_present

Verifica que patrones regex existen en archivos que matchean un glob.

```yaml
- id: check-logging
  name: "Modulos tienen logging"
  type: pattern_present
  glob: "src/**/*.py"
  patterns:
    - "import logging|import structlog"
  required: false
  tags: [quality]
```

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `glob` | string | Patron glob para encontrar archivos (ej: `src/**/*.py`) |
| `patterns` | list[string] | Patrones regex a buscar (case-insensitive) |

Falla si **algun** patron no se encuentra en **algun** archivo que matchea el glob. Es decir, verifica que TODOS los patrones estan presentes en TODOS los archivos.

### pattern_absent

Verifica que patrones regex NO existen en archivos que matchean un glob.

```yaml
- id: check-no-secrets
  name: "Sin secrets hardcodeados"
  type: pattern_absent
  glob: "src/**/*.py"
  patterns:
    - "API_KEY\\s*=\\s*['\"]sk-"
    - "password\\s*=\\s*['\"]\\w{8,}"
  required: true
  tags: [security]
```

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `glob` | string | Patron glob para encontrar archivos |
| `patterns` | list[string] | Patrones regex que NO deben existir (case-insensitive) |

Falla si **algun** patron se encuentra en **algun** archivo.

---

## Campos comunes de cada check

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `id` | string | `"unknown"` | Identificador unico del check |
| `name` | string | mismo que `id` | Nombre descriptivo |
| `type` | string | `"command"` | Tipo de check: `command`, `files_exist`, `pattern_present`, `pattern_absent` |
| `required` | bool | `true` | Si es obligatorio. Los checks no-required pueden fallar sin afectar el exit code. |
| `tags` | list[string] | `[]` | Tags para filtrado con `--tags` |

---

## Tags y filtrado

Los checks pueden tener tags para ejecutar subconjuntos:

```yaml
checks:
  - id: check-tests
    tags: [tests, ci]
    ...
  - id: check-security
    tags: [security, ci]
    ...
  - id: check-docs
    tags: [docs]
    ...
```

```bash
# Solo checks con tag "ci"
intake verify specs/my-spec/ -p . -t ci

# Checks con tag "security" O "tests"
intake verify specs/my-spec/ -p . -t security -t tests
```

Un check se ejecuta si tiene **al menos uno** de los tags especificados.

---

## Fail-fast

Con `--fail-fast`, la verificacion se detiene en el primer check **requerido** que falle:

```bash
intake verify specs/my-spec/ -p . --fail-fast
```

Los checks que no se ejecutaron se cuentan como "skipped" en el reporte.

---

## Formatos de reporte

### Terminal (default)

Tabla Rich con colores:

```
                    Verification Report: my-spec
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ ID        ┃ Check             ┃ Status ┃ Required ┃ Time   ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ check-01  │ Tests pasan       │ PASS   │ Yes      │ 1.2s   │
│ check-02  │ Archivos existen  │ PASS   │ Yes      │ 0.0s   │
│ check-03  │ Auth presente     │ FAIL   │ Yes      │ 0.1s   │
└───────────┴───────────────────┴────────┴──────────┴────────┘
  Passed: 2  Failed: 1  Skipped: 0
```

### JSON

```bash
intake verify specs/my-spec/ -p . -f json
```

```json
{
  "spec_name": "my-spec",
  "total_checks": 3,
  "passed": 2,
  "failed": 1,
  "skipped": 0,
  "all_required_passed": false,
  "results": [
    {
      "id": "check-01",
      "name": "Tests pasan",
      "passed": true,
      "required": true,
      "output": "3 passed in 1.2s",
      "duration_ms": 1200
    }
  ]
}
```

### JUnit XML

```bash
intake verify specs/my-spec/ -p . -f junit > test-results.xml
```

```xml
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="my-spec" tests="3" failures="1" skipped="0">
    <testcase name="Tests pasan" classname="check-01" time="1.200"/>
    <testcase name="Archivos existen" classname="check-02" time="0.001"/>
    <testcase name="Auth presente" classname="check-03" time="0.100">
      <failure message="Pattern 'auth_required' not found in src/routes.py"/>
    </testcase>
  </testsuite>
</testsuites>
```

---

## Integracion con CI/CD

### GitHub Actions (action oficial)

La forma mas simple de integrar verificacion en CI. La action oficial instala intake, ejecuta verify y sube el reporte como artefacto:

```yaml
name: Verify Spec Compliance
on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: Diego303/intake-cli/action@main
        with:
          spec-dir: specs/my-feature/
          report-format: junit
```

Ver [Integracion CI/CD](integracion-cicd.md#action-oficial-de-intake-recomendado) para la referencia completa de inputs y outputs.

### GitHub Actions (manual)

Si prefieres configurar los pasos manualmente:

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

      - name: Install intake
        run: pip install intake-ai-cli

      - name: Run acceptance checks
        run: intake verify specs/my-feature/ -p . -f junit > test-results.xml

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: test-results.xml
```

### Script verify.sh (via export generic)

Si usas el exporter `generic`, se genera un `verify.sh` standalone que no necesita intake instalado:

```bash
# Exportar
intake export specs/my-feature/ -f generic -o output/

# Ejecutar directamente
./output/verify.sh /path/to/project
```

---

## Verificacion continua con watch mode

Para re-ejecutar los checks automaticamente cada vez que cambias un archivo en el proyecto:

```bash
intake watch specs/my-spec/ -p .
```

Esto monitorea el directorio del proyecto con `watchfiles` y re-ejecuta los checks de `acceptance.yaml` en cada cambio. Util durante el desarrollo para ver inmediatamente si la implementacion cumple la spec.

```bash
# Solo checks con tag "tests"
intake watch specs/my-spec/ -p . -t tests

# Debounce mas largo (5 segundos)
intake watch specs/my-spec/ -p . --debounce 5.0
```

Requiere: `pip install "intake-ai-cli[watch]"`

Ver [Watch Mode](watch-mode.md) para documentacion completa.

---

## Verificacion via MCP

Si usas el servidor MCP de intake, los agentes IA pueden ejecutar verificacion programaticamente con el tool `intake_verify`:

```
Tool: intake_verify
Input: { "spec_name": "my-spec", "tags": ["tests"] }
Output: "Verification: 3/4 passed\n[PASS] check-01: Tests pasan\n[FAIL] check-03: ..."
```

Tambien pueden usar el prompt `verify_and_fix` para un ciclo automatico de verificar-corregir-reverificar.

Ver [MCP Server](mcp-server.md) para detalles.

---

## Exit codes

| Codigo | Significado |
|--------|-------------|
| `0` | Todos los checks **requeridos** pasaron (los opcionales pueden haber fallado) |
| `1` | Al menos un check **requerido** fallo |
| `2` | Error de ejecucion (spec no encontrada, YAML invalido, etc.) |
