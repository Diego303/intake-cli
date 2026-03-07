"""Template loader with user override support.

Loading priority:
1. User templates in .intake/templates/ (project-level)
2. Built-in templates in intake/templates/ (package-level)

Users can override ANY built-in template by placing a file with the
same name in their .intake/templates/ directory. This allows teams
to customize the format of requirements.md, CLAUDE.md, etc.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader, Template

from intake.config.schema import TemplatesConfig

logger = structlog.get_logger()


class TemplateLoader:
    """Template loader with user override support.

    Uses Jinja2 ChoiceLoader to search user templates first,
    then fall back to built-in templates.

    Example::

        loader = TemplateLoader(project_dir="./my-project")
        template = loader.get_template("requirements.md.j2")
        output = template.render(functional_requirements=[...])
    """

    def __init__(
        self,
        config: TemplatesConfig | None = None,
        project_dir: str = ".",
    ) -> None:
        self.config = config or TemplatesConfig()
        self.project_dir = Path(project_dir)
        self._env: Environment | None = None
        self._overridden: set[str] = set()

    @property
    def env(self) -> Environment:
        """Lazily create the Jinja2 environment with user override support."""
        if self._env is not None:
            return self._env

        loaders: list[Any] = []

        # 1. User templates (highest priority)
        user_dir = self.project_dir / self.config.user_dir
        if user_dir.exists() and user_dir.is_dir():
            loaders.append(FileSystemLoader(str(user_dir)))
            self._scan_overrides(user_dir)

        # 2. Built-in templates (fallback)
        loaders.append(PackageLoader("intake", "templates"))

        self._env = Environment(
            loader=ChoiceLoader(loaders),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        return self._env

    def get_template(self, name: str) -> Template:
        """Get a template by name, with user override if available.

        Args:
            name: Template filename (e.g. ``requirements.md.j2``).

        Returns:
            Jinja2 Template object.
        """
        template = self.env.get_template(name)

        if name in self._overridden and self.config.warn_on_override:
            logger.info(
                "template_override",
                template=name,
                user_dir=str(self.project_dir / self.config.user_dir),
            )

        return template

    def list_templates(self) -> dict[str, str]:
        """List all available templates with their source.

        Returns:
            Dict of ``{template_name: "builtin" | "user" | "user (override)"}``.
        """
        result: dict[str, str] = {}

        # Built-in templates
        try:
            builtin_loader = PackageLoader("intake", "templates")
            builtin_env = Environment(loader=builtin_loader)
            for name in builtin_env.loader.list_templates():  # type: ignore[union-attr]
                # Exclude non-template files (e.g. .py files in templates/)
                if name.endswith((".j2", ".jinja2")):
                    result[name] = "builtin"
        except Exception:
            pass

        # User templates
        user_dir = self.project_dir / self.config.user_dir
        if user_dir.exists():
            for f in user_dir.iterdir():
                if f.is_file() and f.suffix in (".j2", ".jinja2"):
                    if f.name in result:
                        result[f.name] = "user (override)"
                    else:
                        result[f.name] = "user"

        return result

    def _scan_overrides(self, user_dir: Path) -> None:
        """Detect which built-in templates are overridden by user."""
        try:
            builtin_loader = PackageLoader("intake", "templates")
            builtin_env = Environment(loader=builtin_loader)
            builtin_names = set(builtin_env.loader.list_templates())  # type: ignore[union-attr]
        except Exception:
            return

        for f in user_dir.iterdir():
            if f.is_file() and f.name in builtin_names:
                self._overridden.add(f.name)
                logger.debug("template_override_detected", template=f.name)
