"""MCP server creation and transport setup.

Creates an MCP server with intake tools, resources, and prompts
registered. Supports stdio and SSE transports.

Requires: pip install intake-ai-cli[mcp]
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger()

MCP_SERVER_NAME = "intake-spec"


def create_server(
    specs_dir: str = "./specs",
    project_dir: str = ".",
) -> object:
    """Create and configure the MCP server.

    Requires: pip install intake-ai-cli[mcp]

    Exposes:
    - Tools: intake_show, intake_verify, intake_feedback,
             intake_get_context, intake_get_tasks, intake_update_task,
             intake_list_specs
    - Resources: intake://specs/{name}/requirements, tasks, context, etc.
    - Prompts: implement_next_task, verify_and_fix

    Args:
        specs_dir: Base directory where specs live.
        project_dir: Project directory for verification.

    Returns:
        Configured MCP Server instance.

    Raises:
        ImportError: If the mcp package is not installed.
    """
    try:
        from mcp.server import Server
    except ImportError:
        raise ImportError(
            "MCP server requires the mcp package. Install with: pip install intake-ai-cli[mcp]"
        ) from None

    from intake.mcp.prompts import register_prompts
    from intake.mcp.resources import register_resources
    from intake.mcp.tools import register_tools

    server = Server(MCP_SERVER_NAME)

    register_tools(server, specs_dir, project_dir)
    register_resources(server, specs_dir)
    register_prompts(server, specs_dir)

    logger.info(
        "mcp_server_created",
        specs_dir=specs_dir,
        project_dir=project_dir,
    )
    return server


async def run_stdio(
    specs_dir: str = "./specs",
    project_dir: str = ".",
) -> None:
    """Run the MCP server with stdio transport.

    Blocks until the connection is closed (e.g., the agent disconnects).

    Args:
        specs_dir: Base directory where specs live.
        project_dir: Project directory for verification.

    Raises:
        ImportError: If the mcp package is not installed.
    """
    try:
        from mcp.server.stdio import stdio_server
    except ImportError:
        raise ImportError(
            "MCP server requires the mcp package. Install with: pip install intake-ai-cli[mcp]"
        ) from None

    server = create_server(specs_dir, project_dir)

    logger.info("mcp_server_starting", transport="stdio")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_sse(
    specs_dir: str = "./specs",
    project_dir: str = ".",
    port: int = 8080,
) -> None:
    """Run the MCP server with SSE (Server-Sent Events) transport.

    Starts an HTTP server that accepts SSE connections from remote agents.

    Args:
        specs_dir: Base directory where specs live.
        project_dir: Project directory for verification.
        port: Port to listen on.

    Raises:
        ImportError: If the mcp package is not installed.
    """
    try:
        from mcp.server.sse import SseServerTransport
    except ImportError:
        raise ImportError(
            "MCP SSE transport requires the mcp package. "
            "Install with: pip install intake-ai-cli[mcp]"
        ) from None

    try:
        import uvicorn
        from starlette.applications import Starlette
        from starlette.routing import Route
    except ImportError:
        raise ImportError(
            "MCP SSE transport requires starlette and uvicorn. "
            "Install with: pip install starlette uvicorn"
        ) from None

    server = create_server(specs_dir, project_dir)
    sse = SseServerTransport("/messages")

    async def handle_sse(request: object) -> object:
        async with sse.connect_sse(request) as streams:  # type: ignore[arg-type]
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options(),
            )
        return None  # type: ignore[return-value]

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),  # type: ignore[arg-type]
            Route("/messages", endpoint=sse.handle_post_message),  # type: ignore[arg-type]
        ],
    )

    logger.info("mcp_server_starting", transport="sse", port=port)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    srv = uvicorn.Server(config)
    await srv.serve()
