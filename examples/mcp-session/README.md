# Example: MCP Server Session

Use intake as an MCP server so AI agents (Claude Code, Cursor, etc.) can consume specs in real time during development.

## Prerequisites

```bash
pip install intake-ai-cli[mcp]
```

## Setup

### Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "intake": {
      "command": "intake",
      "args": ["mcp", "serve", "--specs-dir", "./specs", "--project-dir", "."]
    }
  }
}
```

### Cursor

Add to your Cursor MCP settings (Settings > MCP Servers):

```json
{
  "intake": {
    "command": "intake",
    "args": ["mcp", "serve", "--specs-dir", "./specs", "--project-dir", "."]
  }
}
```

### SSE Transport (Remote/IDE)

For HTTP-based integrations:

```bash
intake mcp serve --transport sse --port 8080
```

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `intake_show` | View a spec summary (requirements count, tasks, checks) |
| `intake_get_context` | Read project context (stack, conventions, current state) |
| `intake_get_tasks` | List tasks with optional status filter |
| `intake_update_task` | Mark a task as done, in_progress, blocked |
| `intake_verify` | Run acceptance checks against the implementation |
| `intake_feedback` | Analyze verification failures and get fix suggestions |
| `intake_list_specs` | List all available specs |

## Available MCP Resources

Spec files are exposed as resources via URIs:

```
intake://specs/{spec-name}/requirements
intake://specs/{spec-name}/tasks
intake://specs/{spec-name}/context
intake://specs/{spec-name}/acceptance
intake://specs/{spec-name}/design
intake://specs/{spec-name}/sources
```

## Available MCP Prompts

| Prompt | Description |
|--------|-------------|
| `implement_next_task` | Get instructions to implement the next pending task |
| `verify_and_fix` | Run verification and iteratively fix failures |

## Walkthrough

1. **Generate a spec first:**
   ```bash
   intake init "User auth" -s requirements.md
   ```

2. **Start the MCP server:**
   ```bash
   intake mcp serve
   ```

3. **In your AI agent, use the tools:**

   The agent can now:
   - Read the spec context with `intake_get_context`
   - Get the next task with `intake_get_tasks` (filter by `pending`)
   - Implement the task
   - Mark it done with `intake_update_task`
   - Verify with `intake_verify`
   - If checks fail, get suggestions with `intake_feedback`
   - Repeat until all tasks are done

4. **Use the `implement_next_task` prompt** to get a structured starting point that references the right MCP tools.

## Configuration

In `.intake.yaml`:

```yaml
mcp:
  specs_dir: ./specs       # Where specs live
  project_dir: .           # Project root for verification
  transport: stdio         # stdio | sse
  sse_port: 8080           # Port for SSE transport
```
