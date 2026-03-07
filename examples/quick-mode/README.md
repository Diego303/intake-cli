# Example: Quick Mode (Simple Tasks)

Use `--mode quick` for simple tasks that don't need a full 6-file spec.

## When to Use Quick Mode

Quick mode is ideal for:
- Bug fixes ("Fix the login button color")
- Small style changes ("Update the header font")
- Simple features ("Add a loading spinner to the submit button")
- One-liner tasks from a single short source

Quick mode generates only `context.md` + `tasks.md` — skipping requirements, design, acceptance, and sources files.

## Usage

```bash
# Explicit quick mode
intake init "Fix login button color" -s "The login button should be blue (#0066CC) instead of gray" --mode quick

# From a short file
intake init "Update header" -s bugfix.txt --mode quick

# Auto-detected (when source is short and simple)
intake init "Fix typo in footer" -s "Change 'Copyrigth' to 'Copyright' in the footer"
```

## Auto-Detection

If you don't specify `--mode`, intake auto-detects the complexity:

| Condition | Mode |
|-----------|------|
| 1 source, <500 words, no structured content | **quick** |
| 1-3 sources, <5000 words | **standard** |
| 4+ sources, or >5000 words, or multiple formats | **enterprise** |

Auto-detection can be disabled:

```yaml
spec:
  auto_mode: false  # Always use standard mode unless --mode is specified
```

## Output Comparison

### Quick mode (2 files)

```
specs/fix-login-button-color/
├── context.md       # Project context
└── tasks.md         # Simple task list
```

### Standard mode (6 files + lock)

```
specs/fix-login-button-color/
├── requirements.md
├── design.md
├── tasks.md
├── acceptance.yaml
├── context.md
├── sources.md
└── spec.lock.yaml
```

### Enterprise mode (6 files + detailed risks)

Same as standard, but with detailed risk assessment and richer traceability.

## Example

### Input

```text
The login button on the /login page is gray (#999999).
It should be our brand blue (#0066CC) with white text.
Also add a hover state: darker blue (#004499).
```

### Quick mode output (`tasks.md`)

A focused task list with just the changes needed — no architecture overview, no requirements matrix, no acceptance YAML.

Perfect for feeding directly to an agent:

```bash
intake init "Fix login button" -s button-fix.txt --mode quick --format claude-code
```
