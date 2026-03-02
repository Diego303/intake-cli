"""Auto-detection of a project's tech stack from project files."""

from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger()

# Maps marker files to their associated tech stack components
_STACK_MARKERS: dict[str, list[str]] = {
    "package.json": ["javascript", "node"],
    "tsconfig.json": ["typescript"],
    "pyproject.toml": ["python"],
    "setup.py": ["python"],
    "requirements.txt": ["python"],
    "Pipfile": ["python"],
    "Cargo.toml": ["rust"],
    "go.mod": ["go"],
    "pom.xml": ["java", "maven"],
    "build.gradle": ["java", "gradle"],
    "build.gradle.kts": ["kotlin", "gradle"],
    "Gemfile": ["ruby"],
    "composer.json": ["php"],
    "Dockerfile": ["docker"],
    "docker-compose.yml": ["docker"],
    "docker-compose.yaml": ["docker"],
    ".github/workflows": ["github-actions"],
    "Makefile": ["make"],
    "CMakeLists.txt": ["cmake", "c/c++"],
    "next.config.js": ["nextjs"],
    "next.config.mjs": ["nextjs"],
    "next.config.ts": ["nextjs"],
    "nuxt.config.ts": ["nuxt", "vue"],
    "angular.json": ["angular"],
    "svelte.config.js": ["svelte"],
    "tailwind.config.js": ["tailwindcss"],
    "tailwind.config.ts": ["tailwindcss"],
    "prisma/schema.prisma": ["prisma"],
    "drizzle.config.ts": ["drizzle"],
    ".env": ["dotenv"],
    "terraform": ["terraform"],
}

# Patterns to detect within specific files
_CONTENT_MARKERS: dict[str, dict[str, list[str]]] = {
    "pyproject.toml": {
        "fastapi": ["fastapi"],
        "django": ["django"],
        "flask": ["flask"],
        "sqlalchemy": ["sqlalchemy"],
        "pytest": ["pytest"],
        "pydantic": ["pydantic"],
    },
    "package.json": {
        "react": ["react"],
        "vue": ["vue"],
        "express": ["express"],
        "fastify": ["fastify"],
        "prisma": ["prisma"],
    },
}


def detect_stack(project_dir: str) -> list[str]:
    """Detect the tech stack of a project by inspecting its files.

    Looks for known marker files and inspects key configuration files
    for framework-specific patterns.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Sorted, deduplicated list of detected tech stack components.
    """
    root = Path(project_dir)
    if not root.is_dir():
        logger.warning("project_detect_not_dir", path=project_dir)
        return []

    detected: set[str] = set()

    for marker, techs in _STACK_MARKERS.items():
        marker_path = root / marker
        if marker_path.exists():
            detected.update(techs)

    for filename, patterns in _CONTENT_MARKERS.items():
        file_path = root / filename
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for pattern, techs in patterns.items():
                if pattern in content:
                    detected.update(techs)
        except OSError:
            continue

    result = sorted(detected)
    logger.debug("stack_detected", project_dir=project_dir, stack=", ".join(result))
    return result
