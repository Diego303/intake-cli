"""MCP (Model Context Protocol) server for intake.

Exposes intake tools, resources, and prompts via the MCP protocol,
allowing AI agents to consume specs in real time during development.

Requires: pip install intake-ai-cli[mcp]
"""

from __future__ import annotations

__all__ = ["MCPError", "create_server", "run_sse", "run_stdio"]


class MCPError(Exception):
    """Error during MCP server operations.

    Attributes:
        reason: Human-readable explanation.
        suggestion: Optional hint for the user.
    """

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"MCP error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


def create_server(
    specs_dir: str = "./specs",
    project_dir: str = ".",
) -> object:
    """Create and configure the MCP server.

    Convenience re-export from mcp.server module.
    """
    from intake.mcp.server import create_server as _create

    return _create(specs_dir, project_dir)


async def run_stdio(
    specs_dir: str = "./specs",
    project_dir: str = ".",
) -> None:
    """Run the MCP server with stdio transport.

    Convenience re-export from mcp.server module.
    """
    from intake.mcp.server import run_stdio as _run

    await _run(specs_dir, project_dir)


async def run_sse(
    specs_dir: str = "./specs",
    project_dir: str = ".",
    port: int = 8080,
) -> None:
    """Run the MCP server with SSE transport.

    Convenience re-export from mcp.server module.
    """
    from intake.mcp.server import run_sse as _run

    await _run(specs_dir, project_dir, port=port)
