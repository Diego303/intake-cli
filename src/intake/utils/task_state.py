"""Task state tracking for generated spec tasks.

Reads tasks from the tasks.md file in a spec directory and allows
updating their status (pending, in_progress, done, blocked).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import structlog

logger = structlog.get_logger()

# Valid task statuses.
TaskStatusValue = Literal["pending", "in_progress", "done", "blocked"]

VALID_STATUSES: frozenset[str] = frozenset(
    {
        "pending",
        "in_progress",
        "done",
        "blocked",
    }
)

# Regex to match the status field in tasks.md.
_STATUS_PATTERN = re.compile(
    r"^\*\*Status:\*\*\s*(.+)$",
    re.MULTILINE,
)

# Regex to match a task header.
_TASK_HEADER_PATTERN = re.compile(
    r"^##\s+Task\s+(\d+):\s+(.+)$",
    re.MULTILINE,
)

# Regex to match status column in the summary table.
_TABLE_ROW_PATTERN = re.compile(
    r"^\|\s*(\d+)\s*\|(.+)\|(.+)\|(.+)\|(.+)\|$",
    re.MULTILINE,
)


class TaskStateError(Exception):
    """Error during task state operations.

    Attributes:
        reason: Human-readable explanation.
        suggestion: Optional hint for the user.
    """

    def __init__(self, reason: str, suggestion: str = "") -> None:
        self.reason = reason
        self.suggestion = suggestion
        msg = f"Task state error: {reason}"
        if suggestion:
            msg += f"\n  Hint: {suggestion}"
        super().__init__(msg)


@dataclass
class TaskStatus:
    """Status of a single task.

    Attributes:
        id: Task ID number.
        title: Task title.
        status: Current status.
        description: Task description text.
    """

    id: int
    title: str
    status: str
    description: str = ""


class TaskStateManager:
    """Manages task status within a spec directory.

    Reads and updates the tasks.md file to track implementation progress.

    Args:
        spec_dir: Path to the spec directory containing tasks.md.
    """

    TASKS_FILENAME = "tasks.md"

    def __init__(self, spec_dir: str) -> None:
        self._spec_dir = Path(spec_dir)
        self._tasks_path = self._spec_dir / self.TASKS_FILENAME

    def _ensure_tasks_file(self) -> Path:
        """Ensure the tasks.md file exists.

        Returns:
            Path to the tasks.md file.

        Raises:
            TaskStateError: If the file does not exist.
        """
        if not self._tasks_path.exists():
            raise TaskStateError(
                reason=f"Tasks file not found: {self._tasks_path}",
                suggestion="Run 'intake init' first to generate a spec.",
            )
        return self._tasks_path

    def list_tasks(self, status_filter: list[str] | None = None) -> list[TaskStatus]:
        """List all tasks, optionally filtered by status.

        Args:
            status_filter: If provided, only return tasks with these statuses.

        Returns:
            List of TaskStatus objects.

        Raises:
            TaskStateError: If tasks.md cannot be read or parsed.
        """
        path = self._ensure_tasks_file()
        content = path.read_text(encoding="utf-8")

        tasks = self._parse_tasks(content)

        if status_filter:
            tasks = [t for t in tasks if t.status in status_filter]

        logger.debug(
            "tasks_listed",
            spec_dir=str(self._spec_dir),
            total=len(tasks),
            filter=status_filter,
        )

        return tasks

    def get_task(self, task_id: int) -> TaskStatus:
        """Get a single task by ID.

        Args:
            task_id: Task ID number.

        Returns:
            TaskStatus for the requested task.

        Raises:
            TaskStateError: If the task is not found.
        """
        tasks = self.list_tasks()
        for task in tasks:
            if task.id == task_id:
                return task

        raise TaskStateError(
            reason=f"Task {task_id} not found",
            suggestion=f"Available task IDs: {', '.join(str(t.id) for t in tasks)}",
        )

    def update_task(self, task_id: int, new_status: str, note: str = "") -> TaskStatus:
        """Update the status of a task.

        Modifies the tasks.md file in place, updating both the summary
        table and the task detail section.

        Args:
            task_id: Task ID number.
            new_status: New status value.
            note: Optional note to append.

        Returns:
            Updated TaskStatus.

        Raises:
            TaskStateError: If the task is not found or the status is invalid.
        """
        if new_status not in VALID_STATUSES:
            raise TaskStateError(
                reason=f"Invalid status: {new_status}",
                suggestion=f"Valid statuses: {', '.join(sorted(VALID_STATUSES))}",
            )

        path = self._ensure_tasks_file()
        content = path.read_text(encoding="utf-8")

        # Verify task exists
        task = self._find_task_in_content(content, task_id)
        if task is None:
            raise TaskStateError(
                reason=f"Task {task_id} not found in {path}",
                suggestion="Check the task ID with 'intake task list'.",
            )

        # Update the status in the detail section
        updated_content = self._update_status_in_content(content, task_id, new_status, note)

        # Write back
        path.write_text(updated_content, encoding="utf-8")

        logger.info(
            "task_status_updated",
            task_id=task_id,
            old_status=task.status,
            new_status=new_status,
        )

        return TaskStatus(
            id=task_id,
            title=task.title,
            status=new_status,
            description=task.description,
        )

    def _parse_tasks(self, content: str) -> list[TaskStatus]:
        """Parse all tasks from the tasks.md content.

        Args:
            content: Full content of tasks.md.

        Returns:
            List of parsed TaskStatus objects.
        """
        tasks: list[TaskStatus] = []

        # Find all task headers
        headers = list(_TASK_HEADER_PATTERN.finditer(content))

        for i, match in enumerate(headers):
            task_id = int(match.group(1))
            title = match.group(2).strip()

            # Extract the section between this header and the next one
            start = match.end()
            end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
            section = content[start:end]

            # Extract status
            status_match = _STATUS_PATTERN.search(section)
            status = status_match.group(1).strip() if status_match else "pending"

            # Extract description (first paragraph after the header)
            lines = section.strip().split("\n")
            desc_lines: list[str] = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("**") or stripped.startswith("---"):
                    break
                if stripped:
                    desc_lines.append(stripped)

            tasks.append(
                TaskStatus(
                    id=task_id,
                    title=title,
                    status=status,
                    description="\n".join(desc_lines),
                )
            )

        return tasks

    def _find_task_in_content(self, content: str, task_id: int) -> TaskStatus | None:
        """Find a specific task in the content.

        Args:
            content: Full content of tasks.md.
            task_id: Task ID to find.

        Returns:
            TaskStatus if found, None otherwise.
        """
        tasks = self._parse_tasks(content)
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def _update_status_in_content(
        self,
        content: str,
        task_id: int,
        new_status: str,
        note: str,
    ) -> str:
        """Update the status field for a task in the content.

        Args:
            content: Full content of tasks.md.
            task_id: Task ID to update.
            new_status: New status value.
            note: Optional note to append.

        Returns:
            Updated content string.
        """
        # Find the task header
        headers = list(_TASK_HEADER_PATTERN.finditer(content))
        target_header = None
        next_header_start = len(content)

        for i, match in enumerate(headers):
            if int(match.group(1)) == task_id:
                target_header = match
                if i + 1 < len(headers):
                    next_header_start = headers[i + 1].start()
                break

        if target_header is None:
            return content

        section_start = target_header.end()
        section = content[section_start:next_header_start]

        # Update or insert status field
        status_match = _STATUS_PATTERN.search(section)
        status_line = f"**Status:** {new_status}"
        if note:
            status_line += f" — {note}"

        if status_match:
            new_section = (
                section[: status_match.start()] + status_line + section[status_match.end() :]
            )
        else:
            # Insert status after the first empty line (after description)
            new_section = "\n" + status_line + section

        return content[:section_start] + new_section + content[next_header_start:]
