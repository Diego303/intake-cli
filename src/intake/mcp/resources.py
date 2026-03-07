"""MCP resource definitions for intake.

Provides direct read access to spec files via the MCP resource protocol:
- intake://specs/{name}/requirements
- intake://specs/{name}/tasks
- intake://specs/{name}/context
- intake://specs/{name}/acceptance
- intake://specs/{name}/design
- intake://specs/{name}/sources
"""

from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger()

# Maps resource section names to actual file names.
FILE_MAP: dict[str, str] = {
    "requirements": "requirements.md",
    "tasks": "tasks.md",
    "context": "context.md",
    "acceptance": "acceptance.yaml",
    "design": "design.md",
    "sources": "sources.md",
}

RESOURCE_URI_PREFIX = "intake://specs/"


def register_resources(server: object, specs_dir: str) -> None:
    """Register MCP resources for spec file access.

    Each spec file is exposed as a resource with a URI like
    ``intake://specs/{spec_name}/{section}``.

    Args:
        server: MCP Server instance.
        specs_dir: Base directory where specs live.
    """
    try:
        from mcp.types import Resource
    except ImportError:
        raise ImportError(
            "MCP resources require the mcp package. Install with: pip install intake-ai-cli[mcp]"
        ) from None

    @server.list_resources()  # type: ignore[attr-defined, untyped-decorator]
    async def list_resources() -> list[Resource]:
        resources: list[Resource] = []
        path = Path(specs_dir)
        if not path.exists():
            return resources

        for spec_dir in sorted(path.iterdir()):
            if not spec_dir.is_dir():
                continue
            for key, fname in FILE_MAP.items():
                if (spec_dir / fname).exists():
                    mime = "text/markdown" if fname.endswith(".md") else "text/yaml"
                    resources.append(
                        Resource(
                            uri=f"{RESOURCE_URI_PREFIX}{spec_dir.name}/{key}",
                            name=f"{spec_dir.name}/{key}",
                            description=f"{key} for spec {spec_dir.name}",
                            mimeType=mime,
                        )
                    )

        return resources

    @server.read_resource()  # type: ignore[attr-defined, untyped-decorator]
    async def read_resource(uri: str) -> str:
        """Read a spec file by its MCP resource URI.

        Args:
            uri: Resource URI like ``intake://specs/auth/requirements``.

        Returns:
            File content as a string.

        Raises:
            ValueError: If the URI format is invalid.
            FileNotFoundError: If the spec file does not exist.
        """
        parts = uri.removeprefix(RESOURCE_URI_PREFIX).split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid resource URI: {uri}")

        spec_name, section = parts
        fname = FILE_MAP.get(section)
        if not fname:
            raise ValueError(f"Unknown section: {section}")

        fpath = Path(specs_dir) / spec_name / fname
        if not fpath.exists():
            raise FileNotFoundError(f"File not found: {fpath}")

        content = fpath.read_text(errors="ignore")
        logger.debug(
            "resource_read",
            spec=spec_name,
            section=section,
            length=len(content),
        )
        return content
