# Example: From Markdown

Generate a spec from a single Markdown requirements document.

## Input

- `requirements.md` — A Markdown file with functional and non-functional requirements for a REST API.

## Usage

```bash
# Generate spec with default settings
intake init "REST API user service" -s requirements.md

# Generate with enterprise preset for detailed output
intake init "REST API user service" -s requirements.md --preset enterprise

# Dry run to see what would happen
intake init "REST API user service" -s requirements.md --dry-run
```

## Expected Output

```
specs/rest-api-user-service/
├── requirements.md      # Extracted FR and NFR in EARS format
├── design.md            # Architecture, components, tech decisions
├── tasks.md             # Atomic implementation tasks with dependencies
├── acceptance.yaml      # Executable checks (commands, file checks, patterns)
├── context.md           # Project context for AI agents
├── sources.md           # Traceability back to the original source
└── spec.lock.yaml       # Reproducibility lock
```

## Verify

```bash
# After implementation, verify against the spec
intake verify ./specs/rest-api-user-service -p .
```
