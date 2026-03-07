# Example: Feedback Loop (Verify, Fix, Repeat)

Use `intake feedback` to analyze why verification checks failed and get actionable fix suggestions.

## The Feedback Loop

```
intake verify → failures detected → intake feedback → suggestions for agent → fix → re-verify
```

## Workflow

### 1. Generate a spec

```bash
intake init "REST API for users" -s requirements.md
```

### 2. Implement (manually or with an AI agent)

```bash
# Using Claude Code
intake export ./specs/rest-api-for-users -f claude-code -o .
# Then let the agent implement using CLAUDE.md + task files

# Using Cursor
intake export ./specs/rest-api-for-users -f cursor -o .
```

### 3. Verify the implementation

```bash
intake verify ./specs/rest-api-for-users -p .
```

If some checks fail, you'll see which ones and why.

### 4. Get feedback on failures

```bash
# Basic feedback (runs verify internally if no report provided)
intake feedback ./specs/rest-api-for-users -p .

# With a saved verify report
intake verify ./specs/rest-api-for-users -p . --format json -o report.json
intake feedback ./specs/rest-api-for-users -r report.json

# Get suggestions formatted for your agent
intake feedback ./specs/rest-api-for-users --agent-format claude-code
intake feedback ./specs/rest-api-for-users --agent-format cursor
```

### 5. Auto-apply spec amendments

If the feedback identifies ambiguous requirements, it can suggest spec amendments:

```bash
# Preview amendments (default)
intake feedback ./specs/rest-api-for-users -p .

# Auto-apply amendments to the spec
intake feedback ./specs/rest-api-for-users -p . --apply
```

### 6. Re-verify after fixes

```bash
intake verify ./specs/rest-api-for-users -p .
```

Repeat steps 3-6 until all checks pass.

## Failure Types

The feedback analyzer classifies each failure:

| Type | Description | Action |
|------|-------------|--------|
| `implementation_bug` | Code doesn't match a clear requirement | Fix the code |
| `ambiguous_requirement` | Requirement was unclear | Amend the spec |
| `missing_edge_case` | Edge case not covered by spec | Add new check |
| `environment_issue` | Setup/environment problem | Fix environment |

## Configuration

```yaml
feedback:
  auto_amend_spec: false       # Set to true to auto-apply amendments
  max_suggestions: 10          # Limit suggestions per analysis
  include_code_snippets: true  # Include code examples in suggestions
```

## With Watch Mode

Combine feedback with watch mode for continuous verification:

```bash
# Terminal 1: Watch for changes and auto-verify
intake watch ./specs/rest-api-for-users -p . --verbose

# Terminal 2: When failures appear, get feedback
intake feedback ./specs/rest-api-for-users -p .
```
