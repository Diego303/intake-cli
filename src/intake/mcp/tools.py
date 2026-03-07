"""MCP tool definitions for intake.

Registers 9 tools on the MCP server:
- intake_show: Show spec summary
- intake_get_context: Get project context
- intake_get_tasks: Get tasks with status filtering
- intake_update_task: Update task status
- intake_verify: Run verification checks
- intake_feedback: Analyze failures
- intake_list_specs: List available specs
- intake_validate: Validate spec consistency
- intake_estimate: Estimate LLM cost
"""

from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger()

# Spec file names used across tools.
SPEC_FILES = ("requirements.md", "tasks.md", "context.md", "design.md")

# Maximum content length returned per file section.
MAX_SECTION_LENGTH = 3000


def register_tools(server: object, specs_dir: str, project_dir: str) -> None:
    """Register all MCP tools on the server.

    Args:
        server: MCP Server instance.
        specs_dir: Base directory where specs live.
        project_dir: Project directory for verification.
    """
    try:
        from mcp.types import TextContent, Tool
    except ImportError:
        raise ImportError(
            "MCP tools require the mcp package. Install with: pip install intake-ai-cli[mcp]"
        ) from None

    @server.list_tools()  # type: ignore[attr-defined, untyped-decorator]
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="intake_show",
                description=(
                    "Show a summary of a spec: requirements count, tasks, checks, risks, costs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_name": {
                            "type": "string",
                            "description": "Name of the spec directory (e.g. 'auth-oauth2')",
                        },
                    },
                    "required": ["spec_name"],
                },
            ),
            Tool(
                name="intake_get_context",
                description=(
                    "Get the project context document for this spec. "
                    "Contains tech stack, conventions, and what not to touch."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_name": {"type": "string"},
                    },
                    "required": ["spec_name"],
                },
            ),
            Tool(
                name="intake_get_tasks",
                description=(
                    "Get the list of tasks with their current status. "
                    "Use this to know what to implement next."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_name": {"type": "string"},
                        "status_filter": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "done", "blocked", "all"],
                            "default": "all",
                        },
                    },
                    "required": ["spec_name"],
                },
            ),
            Tool(
                name="intake_update_task",
                description="Update the status of a task after completing or blocking it.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_name": {"type": "string"},
                        "task_id": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "done", "blocked"],
                        },
                        "note": {"type": "string", "default": ""},
                    },
                    "required": ["spec_name", "task_id", "status"],
                },
            ),
            Tool(
                name="intake_verify",
                description=(
                    "Run verification checks against the current project. "
                    "Returns which checks passed and which failed."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_name": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Only run checks with these tags",
                        },
                    },
                    "required": ["spec_name"],
                },
            ),
            Tool(
                name="intake_feedback",
                description=(
                    "Analyze verification failures and get specific suggestions "
                    "on what to fix and how. Call this after intake_verify "
                    "shows failures."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_name": {"type": "string"},
                    },
                    "required": ["spec_name"],
                },
            ),
            Tool(
                name="intake_list_specs",
                description="List all available specs in the project.",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="intake_validate",
                description=(
                    "Validate spec internal consistency. Checks cross-references, "
                    "task dependencies, and acceptance check validity. "
                    "Run this before starting implementation."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_name": {"type": "string"},
                        "strict": {"type": "boolean", "default": False},
                    },
                    "required": ["spec_name"],
                },
            ),
            Tool(
                name="intake_estimate",
                description="Estimate LLM cost for generating or regenerating a spec.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_name": {"type": "string"},
                    },
                    "required": ["spec_name"],
                },
            ),
        ]

    @server.call_tool()  # type: ignore[attr-defined, untyped-decorator]
    async def call_tool(name: str, arguments: dict[str, object]) -> list[TextContent]:
        try:
            if name == "intake_show":
                result = _handle_show(specs_dir, str(arguments["spec_name"]))
            elif name == "intake_get_context":
                result = _handle_get_context(specs_dir, str(arguments["spec_name"]))
            elif name == "intake_get_tasks":
                result = _handle_get_tasks(
                    specs_dir,
                    str(arguments["spec_name"]),
                    str(arguments.get("status_filter", "all")),
                )
            elif name == "intake_update_task":
                result = _handle_update_task(
                    specs_dir,
                    str(arguments["spec_name"]),
                    str(arguments["task_id"]),
                    str(arguments["status"]),
                    str(arguments.get("note", "")),
                )
            elif name == "intake_verify":
                tags_raw = arguments.get("tags")
                tags: list[str] | None = None
                if isinstance(tags_raw, list):
                    tags = [str(t) for t in tags_raw]
                result = _handle_verify(
                    specs_dir,
                    project_dir,
                    str(arguments["spec_name"]),
                    tags,
                )
            elif name == "intake_feedback":
                result = await _handle_feedback(
                    specs_dir,
                    project_dir,
                    str(arguments["spec_name"]),
                )
            elif name == "intake_list_specs":
                result = _handle_list_specs(specs_dir)
            elif name == "intake_validate":
                result = _handle_validate(
                    specs_dir,
                    str(arguments["spec_name"]),
                    bool(arguments.get("strict", False)),
                )
            elif name == "intake_estimate":
                result = _handle_estimate(
                    specs_dir,
                    str(arguments["spec_name"]),
                )
            else:
                result = f"Unknown tool: {name}"

            return [TextContent(type="text", text=result)]

        except Exception as e:
            logger.error("mcp_tool_error", tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error: {e}")]


def _handle_show(specs_dir: str, spec_name: str) -> str:
    """Handle the intake_show tool call.

    Args:
        specs_dir: Base specs directory.
        spec_name: Name of the spec to show.

    Returns:
        Formatted spec summary string.
    """
    spec_path = Path(specs_dir) / spec_name
    if not spec_path.exists():
        return f"Spec '{spec_name}' not found in {specs_dir}"

    parts: list[str] = [f"# Spec: {spec_name}\n"]
    for fname in SPEC_FILES:
        fpath = spec_path / fname
        if fpath.exists():
            content = fpath.read_text(errors="ignore")
            parts.append(f"## {fname}\n{content[:MAX_SECTION_LENGTH]}\n")

    return "\n".join(parts)


def _handle_get_context(specs_dir: str, spec_name: str) -> str:
    """Handle the intake_get_context tool call.

    Args:
        specs_dir: Base specs directory.
        spec_name: Name of the spec.

    Returns:
        Content of context.md or error message.
    """
    context_path = Path(specs_dir) / spec_name / "context.md"
    if not context_path.exists():
        return f"No context.md found for spec '{spec_name}'"
    return context_path.read_text(errors="ignore")


def _handle_get_tasks(specs_dir: str, spec_name: str, status_filter: str) -> str:
    """Handle the intake_get_tasks tool call.

    Uses TaskStateManager for structured task reading when possible,
    with fallback to raw file reading.

    Args:
        specs_dir: Base specs directory.
        spec_name: Name of the spec.
        status_filter: Filter tasks by status ("all" for no filter).

    Returns:
        Formatted task list.
    """
    spec_dir = str(Path(specs_dir) / spec_name)
    tasks_path = Path(specs_dir) / spec_name / "tasks.md"

    if not tasks_path.exists():
        return f"No tasks.md found for spec '{spec_name}'"

    try:
        from intake.utils.task_state import TaskStateManager

        manager = TaskStateManager(spec_dir)
        status_list = [status_filter] if status_filter != "all" else None
        tasks = manager.list_tasks(status_filter=status_list)

        if not tasks:
            if status_filter != "all":
                return f"No tasks with status '{status_filter}'"
            return "No tasks found"

        lines: list[str] = [f"# Tasks: {spec_name}\n"]
        for task in tasks:
            lines.append(f"- Task {task.id}: {task.title} [{task.status}]")
            if task.description:
                lines.append(f"  {task.description[:150]}")
        return "\n".join(lines)

    except Exception as e:
        logger.debug("task_state_manager_fallback", error=str(e), spec=spec_name)
        # Fallback to raw file reading
        content = tasks_path.read_text(errors="ignore")
        if status_filter != "all":
            filtered_lines = [
                line
                for line in content.splitlines()
                if status_filter in line.lower() or line.startswith("#")
            ]
            if filtered_lines:
                return "\n".join(filtered_lines)
            return f"No tasks with status '{status_filter}'"
        return content


def _handle_update_task(
    specs_dir: str,
    spec_name: str,
    task_id: str,
    status: str,
    note: str,
) -> str:
    """Handle the intake_update_task tool call.

    Uses TaskStateManager for structured updates.

    Args:
        specs_dir: Base specs directory.
        spec_name: Name of the spec.
        task_id: Task ID to update.
        status: New status value.
        note: Optional note.

    Returns:
        Success or error message.
    """
    spec_dir = str(Path(specs_dir) / spec_name)
    tasks_path = Path(specs_dir) / spec_name / "tasks.md"

    if not tasks_path.exists():
        return f"No tasks.md found for spec '{spec_name}'"

    try:
        task_id_int = int(task_id)
    except ValueError:
        return f"Invalid task ID: {task_id}. Must be a number."

    try:
        from intake.utils.task_state import TaskStateManager

        manager = TaskStateManager(spec_dir)
        updated = manager.update_task(task_id_int, status, note=note)
        return f"Task {updated.id} updated to '{updated.status}'"

    except Exception as e:
        return f"Failed to update task {task_id}: {e}"


def _handle_verify(
    specs_dir: str,
    project_dir: str,
    spec_name: str,
    tags: list[str] | None,
) -> str:
    """Handle the intake_verify tool call.

    Runs the verification engine against the project.

    Args:
        specs_dir: Base specs directory.
        project_dir: Project directory to verify against.
        spec_name: Name of the spec.
        tags: Optional list of tags to filter checks.

    Returns:
        Formatted verification report.
    """
    from intake.verify.engine import VerificationEngine, VerifyError

    acceptance_path = str(Path(specs_dir) / spec_name / "acceptance.yaml")

    try:
        engine = VerificationEngine(project_dir)
        report = engine.run(acceptance_path, tags=tags)
    except VerifyError as e:
        return f"Verification error: {e}"

    lines: list[str] = [f"Verification: {report.passed}/{report.total_checks} passed\n"]
    for r in report.results:
        icon = "PASS" if r.passed else "FAIL"
        lines.append(f"[{icon}] {r.id}: {r.name}")
        if not r.passed and r.output:
            lines.append(f"   Output: {r.output[:200]}")
        if not r.passed and r.error:
            lines.append(f"   Error: {r.error[:200]}")

    return "\n".join(lines)


async def _handle_feedback(
    specs_dir: str,
    project_dir: str,
    spec_name: str,
) -> str:
    """Handle the intake_feedback tool call.

    Runs verification first, then provides guidance on failures.

    Args:
        specs_dir: Base specs directory.
        project_dir: Project directory.
        spec_name: Name of the spec.

    Returns:
        Verification results with feedback guidance.
    """
    verify_result = _handle_verify(specs_dir, project_dir, spec_name, tags=None)

    return (
        f"{verify_result}\n\n"
        "---\n"
        "To get detailed AI-powered fix suggestions, run:\n"
        f"  intake feedback {specs_dir}/{spec_name} -p {project_dir}\n"
    )


def _handle_list_specs(specs_dir: str) -> str:
    """Handle the intake_list_specs tool call.

    Args:
        specs_dir: Base specs directory.

    Returns:
        Formatted list of available specs.
    """
    path = Path(specs_dir)
    if not path.exists():
        return f"Specs directory not found: {specs_dir}"

    specs = [d.name for d in path.iterdir() if d.is_dir() and (d / "requirements.md").exists()]

    if not specs:
        return "No specs found."

    return "Available specs:\n" + "\n".join(f"  - {s}" for s in sorted(specs))


def _handle_validate(specs_dir: str, spec_name: str, strict: bool) -> str:
    """Handle the intake_validate tool call.

    Args:
        specs_dir: Base specs directory.
        spec_name: Name of the spec to validate.
        strict: Whether to treat warnings as errors.

    Returns:
        Formatted validation report.
    """
    from intake.config.schema import ValidateConfig
    from intake.validate.checker import SpecValidator

    config = ValidateConfig(strict=strict)
    validator = SpecValidator(config)
    report = validator.validate(str(Path(specs_dir) / spec_name))

    lines: list[str] = []
    if report.is_valid:
        lines.append(f"Spec '{spec_name}' is valid")
        lines.append(
            f"   {report.requirements_found} requirements, "
            f"{report.tasks_found} tasks, "
            f"{report.checks_found} checks"
        )
    else:
        lines.append(f"Spec '{spec_name}' has {len(report.errors)} errors")

    for issue in report.issues:
        icon = "ERROR" if issue.severity == "error" else "WARN"
        lines.append(f"  [{icon}] [{issue.category}] {issue.message}")
        if issue.suggestion:
            lines.append(f"     Hint: {issue.suggestion}")

    return "\n".join(lines)


def _handle_estimate(specs_dir: str, spec_name: str) -> str:
    """Handle the intake_estimate tool call.

    Estimates cost by scanning existing spec files for word count.

    Args:
        specs_dir: Base specs directory.
        spec_name: Name of the spec to estimate.

    Returns:
        Formatted cost estimate string.
    """
    from intake.estimate.estimator import CostEstimator

    spec_path = Path(specs_dir) / spec_name
    if not spec_path.exists():
        return f"Spec '{spec_name}' not found in {specs_dir}"

    # Collect all text files in the spec directory
    file_paths = [
        str(f) for f in spec_path.iterdir() if f.is_file() and f.suffix in (".md", ".yaml", ".yml")
    ]

    estimator = CostEstimator()
    result = estimator.estimate_from_files(file_paths)

    lines = [
        f"Cost Estimate for '{spec_name}'",
        f"  Model: {result.model}",
        f"  Mode: {result.mode}{'  (auto-detected)' if result.mode_auto_detected else ''}",
        f"  Input: ~{result.total_input_words:,} words -> ~{result.total_input_tokens:,} tokens",
        f"  Output: ~{result.total_output_tokens:,} tokens (estimated)",
        f"  LLM calls: {result.llm_calls}",
        f"  Estimated cost: {result.formatted_cost} (~30% margin)",
    ]

    for w in result.warnings:
        lines.append(f"  Warning: {w}")

    return "\n".join(lines)
