# Example: From Jira API (Live Connector)

Fetch issues directly from Jira's REST API — no manual export needed.

## Prerequisites

1. Install connector dependencies:
   ```bash
   pip install intake-ai-cli[connectors]
   ```

2. Set environment variables:
   ```bash
   export JIRA_API_TOKEN=your-api-token
   export JIRA_EMAIL=your-email@company.com
   ```

3. Configure your Jira instance in `.intake.yaml`:
   ```yaml
   connectors:
     jira:
       url: https://your-org.atlassian.net
   ```

## Usage

```bash
# Fetch a single issue
intake init "Login feature" -s jira://PROJ-123

# Fetch multiple issues
intake init "Sprint work" -s jira://PROJ-123 -s jira://PROJ-124 -s jira://PROJ-125

# Fetch all issues in a sprint
intake init "Sprint 42" -s "jira://PROJ/sprint/42"

# Fetch issues via JQL query
intake init "Bug batch" -s "jira://PROJ?jql=priority=Critical AND status=Open"

# Combine live API with local files
intake init "Auth system" -s jira://PROJ-100 -s notes.md -s wireframe.png
```

## How It Works

1. intake parses the `jira://` URI and routes it to the Jira connector
2. The connector authenticates via `JIRA_API_TOKEN` + `JIRA_EMAIL`
3. Issues are fetched from the Jira REST API and saved as temporary JSON files
4. The standard Jira parser processes the JSON (same as exported files)
5. Analysis, generation, and export proceed as normal

## Source URI Format

| Pattern | Description |
|---------|-------------|
| `jira://PROJ-123` | Single issue by key |
| `jira://PROJ-1,PROJ-2,PROJ-3` | Multiple issues |
| `jira://PROJ/sprint/42` | All issues in sprint 42 |
| `jira://PROJ?jql=<query>` | JQL query (URL-encoded) |

## Expected Output

```
specs/login-feature/
├── requirements.md      # Requirements from issue summaries + descriptions
├── design.md            # Architecture from issue details and comments
├── tasks.md             # Tasks mapped from Jira issues
├── acceptance.yaml      # Checks from acceptance criteria
├── context.md           # Project context
├── sources.md           # Each requirement traced to its Jira issue key
└── spec.lock.yaml
```

## Troubleshooting

```bash
# Verify your Jira credentials
intake doctor

# Check connector status
intake plugins list
```

Common issues:
- **401 Unauthorized**: Check `JIRA_API_TOKEN` and `JIRA_EMAIL`
- **404 Not Found**: Verify the issue key and Jira URL
- **Connection timeout**: Check network/VPN access to your Jira instance
