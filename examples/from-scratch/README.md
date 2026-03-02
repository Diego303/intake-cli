# Example: From Scratch (Plain Text)

Generate a spec from a free-text description — no structured format needed.

## Input

- `idea.txt` — A plain text description of a feature idea, as you might write it in a Slack message or quick note.

## Usage

```bash
# Generate spec from plain text
intake init "Notification system" -s idea.txt

# Use minimal preset for quick prototyping
intake init "Notification system" -s idea.txt --preset minimal

# Specify language for non-English specs
intake init "Notification system" -s idea.txt --lang es
```

## Expected Output

```
specs/notification-system/
├── requirements.md      # Structured requirements extracted from free text
├── design.md            # Proposed architecture
├── tasks.md             # Implementation plan
├── acceptance.yaml      # Verification checks
├── context.md           # Project context
├── sources.md           # Source traceability
└── spec.lock.yaml
```

## Notes

intake works best with detailed input, but it can handle rough ideas too. The LLM will extract what it can and flag ambiguities as open questions in the spec.
