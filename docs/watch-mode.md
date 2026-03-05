# Watch Mode

El modo watch monitorea archivos del proyecto y re-ejecuta automaticamente los checks de verificacion cuando detecta cambios. Usa `watchfiles` (basado en Rust, eficiente) para la observacion de archivos con debounce configurable.

```
[Cambio en archivo] --> [Filtrado de ignorados] --> [Re-verificacion] --> [Resultado en terminal]
                                    ^                                           |
                                    |___________________________________________|
```

---

## Instalacion

Watch mode requiere la dependencia opcional `watchfiles`:

```bash
pip install intake-ai-cli[watch]
```

Si intentas ejecutar `intake watch` sin tener `watchfiles` instalado, obtendras un mensaje de error con la instruccion de instalacion.

---

## Comando CLI

```bash
intake watch <SPEC_DIR> [OPTIONS]
```

### Argumento

| Argumento | Descripcion |
|-----------|-------------|
| `SPEC_DIR` | Ruta al directorio de la spec (debe existir). Contiene `acceptance.yaml`. |

### Opciones

| Opcion | Default | Descripcion |
|--------|---------|-------------|
| `--project-dir` / `-p` | `.` | Directorio del proyecto a monitorear. |
| `--tags` / `-t` | (ninguno) | Filtrar checks por tags. Repetible para multiples tags. |
| `--debounce` | `2.0` | Segundos de espera despues del ultimo cambio antes de re-verificar. |
| `--verbose` / `-v` | `false` | Salida detallada (activa logging de debug). |

### Ejemplos basicos

```bash
# Watch basico
intake watch specs/auth-system/ -p .

# Con filtrado por tags
intake watch specs/api/ -p . -t tests -t security

# Con debounce personalizado (5 segundos)
intake watch specs/api/ -p . --debounce 5.0

# Con salida verbose
intake watch specs/mi-feature/ -p ./my-project -v
```

---

## Como funciona

1. **Validacion inicial:** verifica que `SPEC_DIR` existe y contiene `acceptance.yaml`. Si no, lanza `WatchError` con sugerencia.
2. **Verificacion inicial:** ejecuta todos los checks (o los filtrados por tags) inmediatamente al iniciar.
3. **Monitoreo recursivo:** observa el directorio del proyecto recursivamente usando `watchfiles`.
4. **Debounce:** espera el intervalo configurado despues del ultimo cambio antes de actuar (default: 2 segundos). Evita re-ejecuciones innecesarias durante ediciones rapidas.
5. **Filtrado de ignorados:** descarta cambios en archivos que matchean patrones de ignorado (`.git`, `__pycache__`, etc.).
6. **Re-verificacion selectiva:** ejecuta los checks relevantes contra el proyecto actualizado.
7. **Display de resultados:** muestra un resumen pass/fail con formato Rich en la terminal.
8. **Continua observando** hasta que el usuario presiona `Ctrl+C`.

### Flujo de cambios detectados

Cuando se detectan cambios:

- Se muestran hasta 5 archivos modificados en la terminal
- Si hay mas de 5, se indica cuantos archivos adicionales cambiaron ("+N more")
- Se ejecutan los checks y se muestra el resultado

```
Changed: src/routes.py, src/models.py, tests/test_routes.py

ALL PASSED (5/5 checks)
```

O en caso de fallos:

```
Changed: src/routes.py

FAILURES DETECTED (3/5 checks)
  FAIL check-03: Endpoints tienen autenticacion
     Pattern 'auth_required' not found in src/routes.py
  FAIL check-04: Tests unitarios pasan
     2 failed, 3 passed in 1.5s
```

---

## Patrones de ignorado

Por defecto, los siguientes patrones se ignoran (no disparan re-verificacion):

| Patron | Descripcion |
|--------|-------------|
| `*.pyc` | Archivos compilados de Python |
| `__pycache__` | Directorios de cache de Python |
| `.git` | Directorio de Git (y subdirectorios) |
| `node_modules` | Dependencias de Node.js |
| `.intake` | Directorio interno de intake |

El filtrado es exhaustivo: se comparan el path completo, el nombre del archivo, y **cada componente** del path contra cada patron. Esto significa que el patron `.git` tambien ignora `.git/objects/abc`, `.git/refs/heads/main`, etc.

Los patrones usan `fnmatch` (glob-style matching), soportando `*`, `?`, `[seq]`, y `[!seq]`.

---

## Configuracion (.intake.yaml)

```yaml
watch:
  debounce_seconds: 2.0     # Segundos de espera despues del ultimo cambio
  ignore_patterns:           # Patrones glob a ignorar
    - "*.pyc"
    - "__pycache__"
    - ".git"
    - "node_modules"
    - ".intake"
    - "*.log"                # Ejemplo: ignorar archivos de log
    - ".venv"                # Ejemplo: ignorar virtualenvs
```

| Campo | Tipo | Default | Descripcion |
|-------|------|---------|-------------|
| `debounce_seconds` | float | `2.0` | Milisegundos de debounce convertidos internamente (`debounce_seconds * 1000`). |
| `ignore_patterns` | list[string] | ver arriba | Patrones glob para ignorar cambios. |

**Nota:** el flag `--debounce` del CLI sobreescribe el valor de `debounce_seconds` en la configuracion.

---

## Arquitectura

### Modulos

| Archivo | Proposito |
|---------|-----------|
| `watch/__init__.py` | Exporta `WatchError` (excepcion del modulo). |
| `watch/watcher.py` | Clase `SpecWatcher` — logica principal de observacion y re-verificacion. |

### Dependencias

```
cli.py
  ↓
watch/watcher.py  →  verify/engine.py (VerificationEngine, VerificationReport)
  ↓
config/schema.py (WatchConfig)
```

El modulo `watch/` **no** importa de `llm/` ni de `analyze/`. Esto asegura que el modo watch funciona completamente offline — solo necesita los archivos spec ya generados.

### Clase SpecWatcher

```python
class SpecWatcher:
    def __init__(self, spec_dir, project_dir, config, tags=None): ...

    # Propiedades
    last_report -> VerificationReport | None   # Ultimo reporte de verificacion

    # Metodos publicos
    run() -> None              # Inicia el watch (bloquea hasta Ctrl+C)
    run_once() -> VerificationReport  # Ejecuta verificacion una sola vez

    # Metodos internos
    _filter_ignored(files, patterns) -> list[str]
    _matches_any(filepath, patterns) -> bool  # staticmethod
    _display_changes(console, relevant) -> None
    _extract_changed_files(changes) -> list[str]
    _run_and_display(console) -> None
```

---

## Uso programatico

```python
from intake.watch.watcher import SpecWatcher
from intake.config.schema import WatchConfig

config = WatchConfig(
    debounce_seconds=3.0,
    ignore_patterns=["*.pyc", "__pycache__", ".git"],
)

watcher = SpecWatcher(
    spec_dir="specs/mi-feature/",
    project_dir=".",
    config=config,
    tags=["tests", "security"],
)

# Ejecutar una sola vez (sin watch continuo)
report = watcher.run_once()
print(f"Passed: {report.passed}/{report.total_checks}")
print(f"All required passed: {report.all_required_passed}")

# O iniciar el watch continuo (bloquea)
watcher.run()
```

El metodo `run_once()` es util para testing y para integraciones donde solo se necesita una verificacion puntual sin el loop de observacion.

---

## Integracion con CI/CD

El modo watch esta disenado para **desarrollo local**, no para CI/CD. En un pipeline de CI, lo recomendable es usar `intake verify` directamente:

```bash
# En CI: verificacion puntual
intake verify specs/mi-feature/ -p . -f junit > test-results.xml

# En desarrollo local: watch continuo
intake watch specs/mi-feature/ -p .
```

Sin embargo, puede combinarse con scripts de pre-commit o hooks de desarrollo:

```bash
# En un script de desarrollo
intake watch specs/mi-feature/ -p . --tags ci --debounce 3.0 &
WATCH_PID=$!

# ... trabajo de desarrollo ...

# Al terminar
kill $WATCH_PID
```

---

## Solucion de problemas

### watchfiles no esta instalado

```
Error: Watch mode requires the watchfiles package.
Install with: pip install intake-ai-cli[watch]
```

**Solucion:** instalar la dependencia opcional:

```bash
pip install intake-ai-cli[watch]
```

### Directorio de spec no encontrado

```
Watch error: Spec directory not found: specs/mi-feature/
  Hint: Run 'intake init' first to generate a spec.
```

**Solucion:** verificar que el path a la spec es correcto, o generar la spec primero con `intake init`.

### acceptance.yaml no encontrado

```
Watch error: acceptance.yaml not found in specs/mi-feature/
  Hint: Run 'intake init' to generate acceptance.yaml.
```

**Solucion:** la spec necesita un archivo `acceptance.yaml` con los checks definidos. Regenerar la spec con `intake init` o crear el archivo manualmente (ver [Verificacion](verificacion.md)).

### Los cambios no disparan re-verificacion

Posibles causas:

1. **El archivo esta en un patron de ignorado.** Revisar `watch.ignore_patterns` en `.intake.yaml`.
2. **El debounce es muy alto.** Reducir con `--debounce 1.0`.
3. **El archivo esta fuera del directorio del proyecto.** Solo se observa el directorio especificado con `--project-dir`.

### Alto consumo de CPU

Si el directorio del proyecto es muy grande (monorepo, muchas dependencias):

1. Agregar patrones de ignorado adicionales en `.intake.yaml`:
   ```yaml
   watch:
     ignore_patterns:
       - "*.pyc"
       - "__pycache__"
       - ".git"
       - "node_modules"
       - ".intake"
       - ".venv"
       - "dist"
       - "build"
       - "*.egg-info"
   ```
2. Aumentar el debounce para reducir la frecuencia de re-verificacion.
3. Usar `--tags` para ejecutar solo un subconjunto de checks.

---

## Exit codes

| Codigo | Significado |
|--------|-------------|
| `0` | Watch terminado normalmente (Ctrl+C). |
| `2` | Error de ejecucion (spec no encontrada, config invalida, watchfiles no instalado). |
