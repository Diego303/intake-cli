# Seguridad

Guia de seguridad para el uso de intake en entornos corporativos y regulados. Cubre el modelo de amenazas, gestion de secretos, redaccion de datos sensibles, modo offline y consideraciones de cumplimiento.

---

## Modelo de amenazas

### Superficie de ataque

| Componente | Riesgo | Mitigacion |
|-----------|--------|------------|
| Llamadas al LLM | Datos de requisitos se envian al proveedor LLM | `redact_patterns` para eliminar datos sensibles; modelos locales para air-gapped |
| Archivos fuente | Fuentes pueden contener secretos, PII, datos regulados | `redact_files` excluye archivos sensibles; redaccion antes del envio |
| Credenciales de conectores | API tokens de Jira/Confluence/GitHub | Variables de entorno, nunca en `.intake.yaml`; rotacion transparente |
| acceptance.yaml | Checks de tipo `command` ejecutan comandos shell arbitrarios | Revisar checks antes de ejecutar `intake verify`; no ejecutar specs de fuentes no confiables |
| Sistema de plugins | Plugins externos ejecutan codigo Python | Solo instalar plugins de fuentes confiables; `intake plugins check` para validar |
| spec.lock.yaml | Contiene hashes y metadata de las fuentes | Solo hashes parciales (16 hex chars), no contenido; seguro para commitear |

### Flujo de datos: que se envia al LLM

```
Fuentes de requisitos
        |
   [ REDACCION ]              <-- security.redact_patterns (regex)
   [ EXCLUSION ]              <-- security.redact_files (glob)
        |
   Texto limpio + metadata
        |
   [ ENVIO AL LLM ]           <-- Solo init, add, feedback
        |
   Respuesta JSON (requisitos, diseno, tareas)
        |
   [ GENERACION LOCAL ]       <-- Todo lo demas es local
        |
   Archivos spec (Markdown/YAML)
```

**Se envia al LLM:**
- Texto extraido de las fuentes (despues de redaccion)
- Informacion del stack tecnologico (auto-detectado)
- Idioma configurado

**NO se envia al LLM:**
- Codigo fuente del proyecto
- API keys ni credenciales
- Contenido de archivos excluidos por `redact_files`
- Resultados de verificacion (excepto en `feedback`)

**Queda 100% local:**
- `intake verify` — ejecucion de checks
- `intake export` — generacion de archivos
- `intake show`, `list`, `diff` — lectura de archivos
- `intake doctor` — checks del entorno
- `intake task` — gestion de estado
- `intake plugins` — listado de plugins

---

## Gestion de secretos

### API keys del LLM

Las API keys **siempre** se leen de variables de entorno. Nunca se almacenan en `.intake.yaml`:

```yaml
# .intake.yaml — solo el NOMBRE de la variable, no el valor
llm:
  api_key_env: ANTHROPIC_API_KEY
```

```bash
# Configurar la variable de entorno
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Patron recomendado para equipos:**

```bash
# .env (en .gitignore — nunca commitear)
ANTHROPIC_API_KEY=sk-ant-api03-tu-key-real

# .env.example (commitear como referencia)
ANTHROPIC_API_KEY=sk-ant-api03-REEMPLAZAR
```

### Tokens de conectores

Mismo patron para Jira, Confluence y GitHub:

```bash
# .env
JIRA_API_TOKEN=tu-token-jira
JIRA_EMAIL=dev@company.com
CONFLUENCE_API_TOKEN=tu-token-confluence
CONFLUENCE_EMAIL=dev@company.com
GITHUB_TOKEN=ghp_tu-personal-access-token
```

Los nombres de las variables son configurables en `.intake.yaml` via `connectors.*.token_env` y `connectors.*.email_env`.

### Rotacion de credenciales

intake no cachea tokens entre ejecuciones. Al rotar una credencial:

1. Actualizar el valor de la variable de entorno
2. La siguiente ejecucion de intake usara el nuevo valor automaticamente

### Secretos en CI/CD

| Plataforma | Mecanismo | Ejemplo |
|-----------|-----------|---------|
| GitHub Actions | `secrets.*` | `${{ secrets.ANTHROPIC_API_KEY }}` |
| GitLab CI | Variables CI/CD (masked) | `$ANTHROPIC_API_KEY` |
| Jenkins | Credentials plugin | `withCredentials([string(...)])` |
| Azure DevOps | Variable groups (secret) | `$(ANTHROPIC_API_KEY)` |

Ver [Integracion CI/CD](integracion-cicd.md) para ejemplos completos.

---

## Redaccion de datos sensibles

### Patrones de redaccion (redact_patterns)

Los patrones son regex aplicados al texto de las fuentes **antes** de enviarlo al LLM:

```yaml
security:
  redact_patterns:
    # API keys y tokens
    - "sk-[a-zA-Z0-9]{20,}"                    # Anthropic API keys
    - "sk-proj-[a-zA-Z0-9]{20,}"               # OpenAI project keys
    - "ghp_[a-zA-Z0-9]{36}"                     # GitHub PATs
    - "xoxb-[a-zA-Z0-9-]+"                      # Slack bot tokens
    - "AKIA[0-9A-Z]{16}"                         # AWS access keys

    # Datos financieros
    - "\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b"  # Numeros de tarjeta
    - "\\b\\d{3}-\\d{2}-\\d{4}\\b"              # SSN (US)

    # Credenciales en texto
    - "password\\s*[:=]\\s*['\"]?\\S+"           # Passwords en configs
    - "secret\\s*[:=]\\s*['\"]?\\S+"             # Secrets en configs
    - "mongodb(\\+srv)?://[^\\s]+"               # Connection strings MongoDB
    - "postgres(ql)?://[^\\s]+"                   # Connection strings PostgreSQL
    - "mysql://[^\\s]+"                           # Connection strings MySQL

    # Datos internos
    - "\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b"  # IPs internas
```

### Exclusion de archivos (redact_files)

Archivos que intake nunca procesara como fuentes:

```yaml
security:
  redact_files:
    # Defaults
    - "*.env"
    - "*.pem"
    - "*.key"

    # Recomendados para enterprise
    - "credentials.*"
    - "secrets.*"
    - "*.pfx"
    - "*.p12"
    - "*.jks"
    - "docker-compose.override.yml"
    - ".env.*"
    - "*.secret"
```

### Verificar la redaccion

Para verificar que los patrones funcionan correctamente:

1. Ejecutar con `--dry-run` para ver que fuentes se procesarian
2. Revisar `spec.lock.yaml` para confirmar que archivos fueron procesados (solo hashes, no contenido)
3. Usar `--preset minimal` con una fuente de prueba para ver el output

---

## Modo offline / air-gapped

### Comandos por modo de conexion

| Comando | Requiere internet | Alternativa offline |
|---------|------------------|---------------------|
| `intake init` | Si (LLM) | Modelo local (Ollama, vLLM) |
| `intake add` | Si (LLM) | Modelo local |
| `intake feedback` | Si (LLM) | Modelo local |
| `intake verify` | No | Funciona offline |
| `intake export` | No | Funciona offline |
| `intake show` | No | Funciona offline |
| `intake list` | No | Funciona offline |
| `intake diff` | No | Funciona offline |
| `intake doctor` | No | Funciona offline |
| `intake task` | No | Funciona offline |
| `intake plugins` | No | Funciona offline |
| Conectores API | Si (APIs externas) | No disponible offline |

### Modelos locales para entornos air-gapped

```yaml
# .intake.yaml para Ollama
llm:
  model: ollama/llama3
  api_key_env: DUMMY_KEY    # Ollama no necesita key
  timeout: 300              # Modelos locales pueden ser mas lentos
```

```bash
export DUMMY_KEY=not-needed

# Verificar que Ollama esta corriendo
ollama list

# Generar spec con modelo local
intake init "Feature" -s reqs.md
```

**Modelos locales soportados** (via LiteLLM):

| Framework | Config de modelo | Ejemplo |
|-----------|-----------------|---------|
| Ollama | `ollama/<model>` | `ollama/llama3`, `ollama/mistral` |
| vLLM | `vllm/<model>` | `vllm/meta-llama/Llama-3-8b` |
| Local OpenAI-compatible | `openai/<model>` + `api_base` | Cualquier servidor OpenAI-compatible |

**Consideraciones:**
- La calidad de extraccion depende del modelo; modelos mas grandes producen mejores specs
- Los modelos locales pueden ser significativamente mas lentos
- Ajustar `timeout` en la configuracion para modelos lentos

### Patron: pre-generar specs para equipos sin LLM

Si solo una persona tiene acceso al LLM:

```bash
# Persona con acceso al LLM genera las specs
intake init "Feature" -s reqs.md
git add specs/ && git commit -m "Add feature spec"
git push

# Equipo sin LLM usa verify, export, task (todo offline)
git pull
intake verify specs/feature/ -p .
intake export specs/feature/ -f claude-code -o .
intake task list specs/feature/
```

---

## Auditoria y trazabilidad

### spec.lock.yaml como artefacto de auditoria

Cada spec incluye un `spec.lock.yaml` que registra:

| Campo | Que contiene | Valor para auditoria |
|-------|-------------|---------------------|
| `created_at` | Timestamp ISO | Cuando se genero la spec |
| `model` | Modelo LLM usado | Reproducibilidad |
| `config_hash` | Hash de la configuracion | Consistencia de parametros |
| `source_hashes` | SHA-256 de cada fuente (16 hex) | Integridad de fuentes |
| `spec_hashes` | SHA-256 de cada archivo spec | Integridad de outputs |
| `total_cost` | Costo en USD | Tracking de gastos |
| `requirement_count` | Cantidad de requisitos | Metricas |
| `task_count` | Cantidad de tareas | Metricas |

**Patron: verificar integridad de fuentes**

Si las fuentes cambian despues de generar la spec, `spec.lock.yaml` lo detecta:

```bash
intake show specs/feature/
# Si las fuentes cambiaron, muestra warning de staleness
```

### Historial de cambios via git

Las specs son archivos de texto ideales para versionado:

```bash
# Comparar versiones
intake diff specs/feature-v1/ specs/feature-v2/

# Historial de cambios
git log --oneline specs/feature/

# Quien cambio que
git blame specs/feature/requirements.md
```

### Trazabilidad bidireccional

intake proporciona trazabilidad completa de requisito a fuente:

```
Fuente original (reqs.md, jira.json)
    ↓ (registrado en sources.md)
Requisito (FR-001 en requirements.md)
    ↓ (referenciado en tasks.md)
Tarea (Task 1: implementar FR-001)
    ↓ (checks en acceptance.yaml)
Verificacion (check-01: tests pasan)
    ↓ (resultados en verify report)
Evidencia de cumplimiento
```

El archivo `sources.md` mapea cada requisito a su fuente original, proporcionando la trazabilidad que auditorias requieren.

---

## Consideraciones de cumplimiento

### Lo que intake proporciona

| Capacidad | Descripcion |
|-----------|-------------|
| Trazabilidad requisito-fuente | `sources.md` mapea cada requisito a su origen |
| Artefacto de auditoria inmutable | `spec.lock.yaml` con hashes y timestamps |
| Verificacion automatizada | `acceptance.yaml` con checks ejecutables |
| Redaccion de datos sensibles | `redact_patterns` y `redact_files` configurables |
| Modo offline | Todo excepto init/add/feedback funciona sin internet |
| Modelos locales | Soporte para Ollama, vLLM (datos nunca salen de la red) |
| Versionado | Specs como archivos de texto, ideales para git |
| Reproducibilidad | `spec.lock.yaml` registra configuracion, modelo y costos |

### Lo que intake NO proporciona

| Aspecto | Estado |
|---------|--------|
| Cifrado de datos en transito | Depende del proveedor LLM (HTTPS) |
| Control de acceso a specs | Depende del sistema de archivos / git |
| Logs de acceso | No genera logs de quien accede a las specs |
| Certificacion de cumplimiento | intake no es una herramienta certificada |
| Cifrado de datos en reposo | Depende del sistema de archivos |
| Retencion de datos automatica | No tiene politicas de retencion; los archivos persisten hasta ser eliminados |

### Recomendaciones por framework

| Framework | Recomendaciones con intake |
|-----------|---------------------------|
| **SOC2** | Usar `redact_patterns` + commitear `spec.lock.yaml` + mantener git history de specs + JUnit en CI como evidencia |
| **HIPAA** | Modelo local (air-gapped) + redaccion agresiva de PHI + nunca usar conectores con datos de pacientes + revisar specs manualmente |
| **ISO 27001** | Documentar intake en inventario de activos + usar preset `enterprise` + habilitar `generate_lock` + redaccion de IPs y hostnames internos |
| **GDPR** | Redactar PII de fuentes antes de procesar + modelo local si los datos no pueden salir de la jurisdiccion + documentar base legal para el procesamiento |

---

## Checklist de seguridad para equipos

- [ ] API keys configuradas via variables de entorno (no en `.intake.yaml`)
- [ ] `.env` agregado a `.gitignore`
- [ ] `redact_patterns` configurados para el tipo de datos del proyecto
- [ ] `redact_files` incluye patrones de credenciales del proyecto
- [ ] Specs revisadas antes de compartir externamente
- [ ] `acceptance.yaml` revisado antes de ejecutar `verify` (checks `command`)
- [ ] Solo plugins de fuentes confiables instalados
- [ ] `spec.lock.yaml` commiteado junto con las specs
- [ ] CI/CD usa secrets management para API keys
- [ ] Modelo local evaluado si los datos son sensibles
