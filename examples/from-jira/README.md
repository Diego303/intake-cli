# Example: From Jira Export

Generate a spec from a Jira JSON export containing multiple issues.

## Input

- `jira-export.json` — A Jira REST API export with 3 issues (including comments, labels, priorities, and issue links).

## How to Export from Jira

1. Use the Jira REST API: `GET /rest/api/2/search?jql=project=PROJ&fields=summary,description,priority,status,labels,comment,issuelinks`
2. Save the response as a JSON file

intake auto-detects Jira format from the JSON structure (no manual format flag needed).

## Usage

```bash
# Generate spec from Jira export
intake init "Payment processing" -s jira-export.json

# With stack hint for better analysis
intake init "Payment processing" -s jira-export.json --stack python,fastapi,postgresql
```

## Expected Output

```
specs/payment-processing/
├── requirements.md      # Requirements extracted from issue summaries + descriptions
├── design.md            # Architecture based on issue details and comments
├── tasks.md             # Tasks mapped from Jira issues
├── acceptance.yaml      # Checks derived from acceptance criteria in descriptions
├── context.md           # Project context
├── sources.md           # Traceability: each requirement → Jira issue key
└── spec.lock.yaml
```
