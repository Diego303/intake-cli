"""Tests for the template loader with user override support."""

from __future__ import annotations

from pathlib import Path

from intake.config.schema import TemplatesConfig
from intake.templates.loader import TemplateLoader


class TestGetTemplate:
    """Tests for TemplateLoader.get_template()."""

    def test_loads_builtin_template(self) -> None:
        loader = TemplateLoader()
        template = loader.get_template("requirements.md.j2")
        assert template is not None

    def test_user_override_takes_priority(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".intake" / "templates"
        user_dir.mkdir(parents=True)
        (user_dir / "requirements.md.j2").write_text("CUSTOM: {{ title }}")

        loader = TemplateLoader(project_dir=str(tmp_path))
        template = loader.get_template("requirements.md.j2")
        result = template.render(title="Test")
        assert "CUSTOM: Test" in result

    def test_fallback_to_builtin_when_no_user_override(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".intake" / "templates"
        user_dir.mkdir(parents=True)
        # No matching file in user dir

        loader = TemplateLoader(project_dir=str(tmp_path))
        template = loader.get_template("requirements.md.j2")
        # Should not raise, loads from builtin
        assert template is not None

    def test_user_only_template(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".intake" / "templates"
        user_dir.mkdir(parents=True)
        (user_dir / "custom_report.md.j2").write_text("Report: {{ data }}")

        loader = TemplateLoader(project_dir=str(tmp_path))
        template = loader.get_template("custom_report.md.j2")
        result = template.render(data="hello")
        assert "Report: hello" in result

    def test_no_user_dir_uses_builtin_only(self, tmp_path: Path) -> None:
        loader = TemplateLoader(project_dir=str(tmp_path))
        template = loader.get_template("requirements.md.j2")
        assert template is not None


class TestListTemplates:
    """Tests for TemplateLoader.list_templates()."""

    def test_lists_builtin_templates(self) -> None:
        loader = TemplateLoader()
        templates = loader.list_templates()
        assert len(templates) > 0
        assert all(v == "builtin" for v in templates.values())

    def test_user_only_template_listed(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".intake" / "templates"
        user_dir.mkdir(parents=True)
        (user_dir / "my_custom.j2").write_text("custom")

        loader = TemplateLoader(project_dir=str(tmp_path))
        templates = loader.list_templates()
        assert templates.get("my_custom.j2") == "user"

    def test_user_override_listed_as_override(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".intake" / "templates"
        user_dir.mkdir(parents=True)
        (user_dir / "requirements.md.j2").write_text("override")

        loader = TemplateLoader(project_dir=str(tmp_path))
        templates = loader.list_templates()
        assert templates.get("requirements.md.j2") == "user (override)"

    def test_empty_user_dir_shows_only_builtin(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".intake" / "templates"
        user_dir.mkdir(parents=True)

        loader = TemplateLoader(project_dir=str(tmp_path))
        templates = loader.list_templates()
        assert all(v == "builtin" for v in templates.values())


class TestOverrideDetection:
    """Tests for override detection and warning."""

    def test_override_detected_in_internal_set(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".intake" / "templates"
        user_dir.mkdir(parents=True)
        (user_dir / "requirements.md.j2").write_text("override")

        loader = TemplateLoader(project_dir=str(tmp_path))
        # Trigger lazy env creation
        _ = loader.env
        assert "requirements.md.j2" in loader._overridden

    def test_no_override_when_user_file_is_unique(self, tmp_path: Path) -> None:
        user_dir = tmp_path / ".intake" / "templates"
        user_dir.mkdir(parents=True)
        (user_dir / "unique_template.j2").write_text("unique")

        loader = TemplateLoader(project_dir=str(tmp_path))
        _ = loader.env
        assert "unique_template.j2" not in loader._overridden


class TestCustomConfig:
    """Tests for custom TemplatesConfig."""

    def test_custom_user_dir(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "my-templates"
        custom_dir.mkdir()
        (custom_dir / "test.j2").write_text("hello {{ name }}")

        config = TemplatesConfig(user_dir="my-templates")
        loader = TemplateLoader(config=config, project_dir=str(tmp_path))
        template = loader.get_template("test.j2")
        assert template.render(name="world") == "hello world"

    def test_env_is_lazily_created(self) -> None:
        loader = TemplateLoader()
        assert loader._env is None
        _ = loader.env
        assert loader._env is not None

    def test_env_cached_after_first_access(self) -> None:
        loader = TemplateLoader()
        env1 = loader.env
        env2 = loader.env
        assert env1 is env2
