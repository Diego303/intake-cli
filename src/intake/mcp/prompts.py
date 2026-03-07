"""MCP prompt templates for intake.

Provides structured starting points for AI agents:
- implement_next_task: Get context + next pending task + checks
- verify_and_fix: Run verify then fix loop
"""

from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger()


def register_prompts(server: object, specs_dir: str) -> None:
    """Register MCP prompt templates.

    Prompts provide structured starting points for agents
    working with intake specs.

    Args:
        server: MCP Server instance.
        specs_dir: Base directory where specs live.
    """
    try:
        from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent
    except ImportError:
        raise ImportError(
            "MCP prompts require the mcp package. Install with: pip install intake-ai-cli[mcp]"
        ) from None

    @server.list_prompts()  # type: ignore[attr-defined, untyped-decorator]
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="implement_next_task",
                description=(
                    "Get the next pending task with full context and "
                    "verification checks. Start here when implementing."
                ),
                arguments=[
                    PromptArgument(
                        name="spec_name",
                        description="Name of the spec",
                        required=True,
                    ),
                ],
            ),
            Prompt(
                name="verify_and_fix",
                description=(
                    "Run verification, analyze failures, and get specific fix instructions."
                ),
                arguments=[
                    PromptArgument(
                        name="spec_name",
                        description="Name of the spec",
                        required=True,
                    ),
                ],
            ),
        ]

    @server.get_prompt()  # type: ignore[attr-defined, untyped-decorator]
    async def get_prompt(
        name: str,
        arguments: dict[str, str] | None = None,
    ) -> list[PromptMessage]:
        args = arguments or {}
        spec_name = args.get("spec_name", "")
        spec_path = Path(specs_dir) / spec_name

        if name == "implement_next_task":
            return _build_implement_prompt(spec_path, spec_name)
        elif name == "verify_and_fix":
            return _build_verify_prompt(spec_path, spec_name)
        else:
            return [
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=f"Unknown prompt: {name}"),
                )
            ]


def _build_implement_prompt(
    spec_path: Path,
    spec_name: str,
) -> list[object]:
    """Build the implement_next_task prompt.

    Includes full spec context (context.md, requirements.md, tasks.md)
    and instructions for the agent.

    Args:
        spec_path: Path to the spec directory.
        spec_name: Name of the spec.

    Returns:
        List of PromptMessage objects.
    """
    from mcp.types import PromptMessage, TextContent

    context_parts: list[str] = []
    for fname in ("context.md", "requirements.md", "tasks.md"):
        fpath = spec_path / fname
        if fpath.exists():
            context_parts.append(f"\n\n## {fname}\n{fpath.read_text(errors='ignore')}")

    context = "".join(context_parts)

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"I'm working on spec '{spec_name}'. Here is the full context:\n"
                    f"{context}\n\n"
                    "Please:\n"
                    "1. Read the tasks and find the next pending task\n"
                    "2. Implement it following the design in design.md\n"
                    "3. After implementing, use intake_verify to check your work\n"
                    "4. Use intake_update_task to mark the task as done\n"
                    "5. Move on to the next pending task"
                ),
            ),
        )
    ]


def _build_verify_prompt(
    spec_path: Path,
    spec_name: str,
) -> list[object]:
    """Build the verify_and_fix prompt.

    Provides instructions for the agent to verify and iteratively fix
    failing checks.

    Args:
        spec_path: Path to the spec directory.
        spec_name: Name of the spec.

    Returns:
        List of PromptMessage objects.
    """
    from mcp.types import PromptMessage, TextContent

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"Run intake_verify for spec '{spec_name}' and analyze the results.\n\n"
                    "For each failing check:\n"
                    "1. Determine what went wrong\n"
                    "2. Fix the code to make the check pass\n"
                    "3. Re-run intake_verify to confirm the fix\n"
                    "4. Repeat until all required checks pass"
                ),
            ),
        )
    ]
