# Security

Security guide for using intake in corporate and regulated environments. Covers the threat model, secrets management, sensitive data redaction, offline mode, and compliance considerations.

---

## Threat Model

### Attack Surface

| Component | Risk | Mitigation |
|-----------|------|------------|
| LLM calls | Requirement data is sent to the LLM provider | `redact_patterns` to strip sensitive data; local models for air-gapped environments |
| Source files | Sources may contain secrets, PII, or regulated data | `redact_files` excludes sensitive files; redaction applied before sending |
| Connector credentials | API tokens for Jira/Confluence/GitHub | Environment variables, never stored in `.intake.yaml`; transparent rotation |
| acceptance.yaml | `command`-type checks execute arbitrary shell commands | Review checks before running `intake verify`; never run specs from untrusted sources |
| Plugin system | External plugins execute Python code | Only install plugins from trusted sources; `intake plugins check` to validate |
| spec.lock.yaml | Contains hashes and metadata from sources | Only partial hashes (16 hex chars), no content; safe to commit |

### Data Flow: What Gets Sent to the LLM

```
Requirement sources
        |
   [ REDACTION ]              <-- security.redact_patterns (regex)
   [ EXCLUSION ]              <-- security.redact_files (glob)
        |
   Clean text + metadata
        |
   [ SENT TO LLM ]           <-- Only init, add, feedback
        |
   JSON response (requirements, design, tasks)
        |
   [ LOCAL GENERATION ]      <-- Everything else is local
        |
   Spec files (Markdown/YAML)
```

**Sent to the LLM:**
- Extracted text from sources (after redaction)
- Tech stack information (auto-detected)
- Configured language

**NOT sent to the LLM:**
- Project source code
- API keys or credentials
- Content of files excluded by `redact_files`
- Verification results (except during `feedback`)

**Stays 100% local:**
- `intake verify` — check execution
- `intake export` — file generation
- `intake show`, `list`, `diff` — file reading
- `intake doctor` — environment checks
- `intake task` — state management
- `intake plugins` — plugin listing

---

## Secrets Management

### LLM API Keys

API keys are **always** read from environment variables. They are never stored in `.intake.yaml`:

```yaml
# .intake.yaml — only the variable NAME, not the value
llm:
  api_key_env: ANTHROPIC_API_KEY
```

```bash
# Set the environment variable
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Recommended pattern for teams:**

```bash
# .env (in .gitignore — never commit)
ANTHROPIC_API_KEY=sk-ant-api03-your-real-key

# .env.example (commit as reference)
ANTHROPIC_API_KEY=sk-ant-api03-REPLACE-ME
```

### Connector Tokens

Same pattern for Jira, Confluence, and GitHub:

```bash
# .env
JIRA_API_TOKEN=your-jira-token
JIRA_EMAIL=dev@company.com
CONFLUENCE_API_TOKEN=your-confluence-token
CONFLUENCE_EMAIL=dev@company.com
GITHUB_TOKEN=ghp_your-personal-access-token
```

Variable names are configurable in `.intake.yaml` via `connectors.*.token_env` and `connectors.*.email_env`.

### Credential Rotation

intake does not cache tokens between executions. When rotating a credential:

1. Update the environment variable value
2. The next intake execution will automatically use the new value

### Secrets in CI/CD

| Platform | Mechanism | Example |
|----------|-----------|---------|
| GitHub Actions | `secrets.*` | `${{ secrets.ANTHROPIC_API_KEY }}` |
| GitLab CI | CI/CD Variables (masked) | `$ANTHROPIC_API_KEY` |
| Jenkins | Credentials plugin | `withCredentials([string(...)])` |
| Azure DevOps | Variable groups (secret) | `$(ANTHROPIC_API_KEY)` |

See [CI/CD Integration](docs/integracion-cicd.md) for complete examples.

---

## Sensitive Data Redaction

### Redaction Patterns (redact_patterns)

Patterns are regex applied to source text **before** sending it to the LLM:

```yaml
security:
  redact_patterns:
    # API keys and tokens
    - "sk-[a-zA-Z0-9]{20,}"                    # Anthropic API keys
    - "sk-proj-[a-zA-Z0-9]{20,}"               # OpenAI project keys
    - "ghp_[a-zA-Z0-9]{36}"                     # GitHub PATs
    - "xoxb-[a-zA-Z0-9-]+"                      # Slack bot tokens
    - "AKIA[0-9A-Z]{16}"                         # AWS access keys

    # Financial data
    - "\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b"  # Credit card numbers
    - "\\b\\d{3}-\\d{2}-\\d{4}\\b"              # SSN (US)

    # Credentials in text
    - "password\\s*[:=]\\s*['\"]?\\S+"           # Passwords in configs
    - "secret\\s*[:=]\\s*['\"]?\\S+"             # Secrets in configs
    - "mongodb(\\+srv)?://[^\\s]+"               # MongoDB connection strings
    - "postgres(ql)?://[^\\s]+"                   # PostgreSQL connection strings
    - "mysql://[^\\s]+"                           # MySQL connection strings

    # Internal data
    - "\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b"  # Internal IPs
```

### File Exclusion (redact_files)

Files that intake will never process as sources:

```yaml
security:
  redact_files:
    # Defaults
    - "*.env"
    - "*.pem"
    - "*.key"

    # Recommended for enterprise
    - "credentials.*"
    - "secrets.*"
    - "*.pfx"
    - "*.p12"
    - "*.jks"
    - "docker-compose.override.yml"
    - ".env.*"
    - "*.secret"
```

### Verifying Redaction

To verify that patterns are working correctly:

1. Run with `--dry-run` to see which sources would be processed
2. Check `spec.lock.yaml` to confirm which files were processed (only hashes, no content)
3. Use `--preset minimal` with a test source to inspect the output

---

## Offline / Air-Gapped Mode

### Commands by Connectivity Requirement

| Command | Requires internet | Offline alternative |
|---------|-------------------|---------------------|
| `intake init` | Yes (LLM) | Local model (Ollama, vLLM) |
| `intake add` | Yes (LLM) | Local model |
| `intake feedback` | Yes (LLM) | Local model |
| `intake verify` | No | Works offline |
| `intake export` | No | Works offline |
| `intake show` | No | Works offline |
| `intake list` | No | Works offline |
| `intake diff` | No | Works offline |
| `intake doctor` | No | Works offline |
| `intake task` | No | Works offline |
| `intake plugins` | No | Works offline |
| API Connectors | Yes (external APIs) | Not available offline |

### Local Models for Air-Gapped Environments

```yaml
# .intake.yaml for Ollama
llm:
  model: ollama/llama3
  api_key_env: DUMMY_KEY    # Ollama doesn't need a key
  timeout: 300              # Local models may be slower
```

```bash
export DUMMY_KEY=not-needed

# Verify Ollama is running
ollama list

# Generate spec with local model
intake init "Feature" -s reqs.md
```

**Supported local models** (via LiteLLM):

| Framework | Model config | Example |
|-----------|-------------|---------|
| Ollama | `ollama/<model>` | `ollama/llama3`, `ollama/mistral` |
| vLLM | `vllm/<model>` | `vllm/meta-llama/Llama-3-8b` |
| Local OpenAI-compatible | `openai/<model>` + `api_base` | Any OpenAI-compatible server |

**Considerations:**
- Extraction quality depends on the model; larger models produce better specs
- Local models may be significantly slower
- Adjust `timeout` in the configuration for slow models

### Pattern: Pre-Generate Specs for Teams Without LLM Access

If only one person has LLM access:

```bash
# Person with LLM access generates the specs
intake init "Feature" -s reqs.md
git add specs/ && git commit -m "Add feature spec"
git push

# Team without LLM uses verify, export, task (all offline)
git pull
intake verify specs/feature/ -p .
intake export specs/feature/ -f claude-code -o .
intake task list specs/feature/
```

---

## Audit and Traceability

### spec.lock.yaml as an Audit Artifact

Each spec includes a `spec.lock.yaml` that records:

| Field | Contents | Audit value |
|-------|----------|-------------|
| `created_at` | ISO timestamp | When the spec was generated |
| `model` | LLM model used | Reproducibility |
| `config_hash` | Hash of the configuration | Parameter consistency |
| `source_hashes` | SHA-256 of each source (16 hex) | Source integrity |
| `spec_hashes` | SHA-256 of each spec file | Output integrity |
| `total_cost` | Cost in USD | Expense tracking |
| `requirement_count` | Number of requirements | Metrics |
| `task_count` | Number of tasks | Metrics |

**Pattern: Verify source integrity**

If sources change after generating the spec, `spec.lock.yaml` detects it:

```bash
intake show specs/feature/
# If sources changed, shows staleness warning
```

### Change History via Git

Specs are text files ideal for version control:

```bash
# Compare versions
intake diff specs/feature-v1/ specs/feature-v2/

# Change history
git log --oneline specs/feature/

# Who changed what
git blame specs/feature/requirements.md
```

### Bidirectional Traceability

intake provides complete traceability from requirement to source:

```
Original source (reqs.md, jira.json)
    ↓ (recorded in sources.md)
Requirement (FR-001 in requirements.md)
    ↓ (referenced in tasks.md)
Task (Task 1: implement FR-001)
    ↓ (checks in acceptance.yaml)
Verification (check-01: tests pass)
    ↓ (results in verify report)
Compliance evidence
```

The `sources.md` file maps each requirement to its original source, providing the traceability that audits require.

---

## Compliance Considerations

### What intake Provides

| Capability | Description |
|------------|-------------|
| Requirement-to-source traceability | `sources.md` maps each requirement to its origin |
| Immutable audit artifact | `spec.lock.yaml` with hashes and timestamps |
| Automated verification | `acceptance.yaml` with executable checks |
| Sensitive data redaction | Configurable `redact_patterns` and `redact_files` |
| Offline mode | Everything except init/add/feedback works without internet |
| Local models | Support for Ollama, vLLM (data never leaves the network) |
| Version control | Specs as text files, ideal for git |
| Reproducibility | `spec.lock.yaml` records configuration, model, and costs |

### What intake Does NOT Provide

| Aspect | Status |
|--------|--------|
| Data encryption in transit | Depends on the LLM provider (HTTPS) |
| Access control for specs | Depends on the file system / git |
| Access logs | Does not generate logs of who accesses specs |
| Compliance certification | intake is not a certified tool |
| Data encryption at rest | Depends on the file system |
| Automatic data retention | No retention policies; files persist until deleted |

### Recommendations by Framework

| Framework | Recommendations with intake |
|-----------|----------------------------|
| **SOC2** | Use `redact_patterns` + commit `spec.lock.yaml` + maintain git history of specs + JUnit in CI as evidence |
| **HIPAA** | Local model (air-gapped) + aggressive PHI redaction + never use connectors with patient data + manual spec review |
| **ISO 27001** | Document intake in asset inventory + use `enterprise` preset + enable `generate_lock` + redact internal IPs and hostnames |
| **GDPR** | Redact PII from sources before processing + local model if data cannot leave the jurisdiction + document legal basis for processing |

---

## Reporting a Vulnerability

If you discover a security vulnerability in intake, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainers at the address listed in the repository's contact information
3. Include a description of the vulnerability, steps to reproduce, and potential impact
4. Allow reasonable time for a fix before public disclosure

We aim to acknowledge reports within 48 hours and provide a fix within 7 days for critical issues.

---

## Security Checklist for Teams

- [ ] API keys configured via environment variables (not in `.intake.yaml`)
- [ ] `.env` added to `.gitignore`
- [ ] `redact_patterns` configured for the project's data types
- [ ] `redact_files` includes the project's credential patterns
- [ ] Specs reviewed before sharing externally
- [ ] `acceptance.yaml` reviewed before running `verify` (`command` checks)
- [ ] Only plugins from trusted sources installed
- [ ] `spec.lock.yaml` committed alongside specs
- [ ] CI/CD uses secrets management for API keys
- [ ] Local model evaluated if data is sensitive
