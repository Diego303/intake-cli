# Example: From GitLab API (Live Connector)

Fetch issues directly from GitLab's REST API — works with GitLab.com (SaaS),
self-hosted GitLab CE/EE, and local instances.

## Prerequisites

1. Install connector dependencies:
   ```bash
   pip install intake-ai-cli[connectors]
   ```

2. Set environment variable:
   ```bash
   export GITLAB_TOKEN=your-personal-access-token
   ```

3. Configure your GitLab instance in `.intake.yaml`:
   ```yaml
   connectors:
     gitlab:
       url: https://gitlab.com  # or https://gitlab.mycompany.com
       include_comments: true
       include_merge_requests: false
   ```

## Usage

```bash
# Fetch a single issue
intake init "SSO login" -s gitlab://mygroup/myproject/issues/42

# Fetch multiple issues
intake init "Sprint work" -s gitlab://mygroup/myproject/issues/42,43,44

# Fetch issues by label and state
intake init "Bug batch" -s "gitlab://mygroup/myproject/issues?labels=bug&state=opened"

# Fetch all issues in a milestone
intake init "v2.0 release" -s gitlab://mygroup/myproject/milestones/3/issues

# Combine API with local files
intake init "Auth system" -s gitlab://mygroup/myproject/issues/42 -s notes.md

# Works with nested groups
intake init "Feature" -s gitlab://org/team/subgroup/project/issues/10
```

## Offline Mode (from exported JSON)

You can also use a manually exported JSON file:

```bash
intake init "SSO login" -s gitlab-issues.json
```

See [gitlab-issues.json](gitlab-issues.json) for the expected format.

## How It Works

1. intake parses the `gitlab://` URI and routes it to the GitLab connector
2. The connector authenticates via `GITLAB_TOKEN` (personal or project access token)
3. Issues are fetched from the GitLab API v4 and saved as temporary JSON files
4. The GitLab Issues parser extracts titles, descriptions, labels, milestones, weights, assignees, discussion notes, and linked merge requests
5. Analysis, generation, and export proceed as normal

## Source URI Format

| Pattern | Description |
|---------|-------------|
| `gitlab://group/project/issues/42` | Single issue by IID |
| `gitlab://group/project/issues/42,43` | Multiple issues |
| `gitlab://group/project/issues?labels=bug` | Filtered by labels |
| `gitlab://group/project/issues?state=opened` | Filtered by state |
| `gitlab://group/project/milestones/3/issues` | All issues in milestone |
| `gitlab://org/sub/project/issues/10` | Nested group support |

## Self-Hosted GitLab

For self-hosted instances with self-signed certificates:

```yaml
connectors:
  gitlab:
    url: https://gitlab.internal.mycompany.com
    ssl_verify: false
```

## Troubleshooting

```bash
# Verify your GitLab credentials
intake doctor

# Check connector status
intake plugins list
```

Common issues:
- **401 Unauthorized**: Check `GITLAB_TOKEN` and ensure it has `read_api` scope
- **404 Not Found**: Verify the project path (group/project format)
- **SSL errors**: Set `ssl_verify: false` for self-signed certificates
