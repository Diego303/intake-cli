# Example: Multi-Source Input

Combine multiple input files of different formats into a single unified spec.

## Inputs

- `user-stories.md` — Markdown with user stories and acceptance criteria
- `api-decisions.json` — Jira export with API design decisions and tech debt items
- `notes.txt` — Plain text meeting notes with additional context

## Usage

```bash
# Generate spec from multiple sources
intake init "E-commerce cart" -s user-stories.md -s api-decisions.json -s notes.txt

# With stack hint
intake init "E-commerce cart" -s user-stories.md -s api-decisions.json -s notes.txt --stack python,django,postgresql
```

## Expected Output

```
specs/e-commerce-cart/
├── requirements.md      # Merged requirements from all three sources
├── design.md            # Architecture reflecting all inputs
├── tasks.md             # Unified task list
├── acceptance.yaml      # Combined verification checks
├── context.md           # Project context
├── sources.md           # Traceability to each source file + Jira keys
└── spec.lock.yaml
```

## Notes

When using multiple sources, intake merges content from all files before analysis. The `sources.md` file traces each requirement back to its originating file, so you can always tell where a requirement came from.

Supported combinations include any mix of: Markdown, Jira JSON, plain text, YAML, PDF, DOCX, Confluence HTML, and images.
