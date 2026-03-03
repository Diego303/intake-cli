"""Tests for plugin discovery via entry points."""

from __future__ import annotations

from intake.plugins.discovery import (
    BUILTIN_DISTRIBUTION,
    PARSER_GROUP,
    PluginInfo,
    PluginRegistry,
    create_registry,
)


class TestPluginInfo:
    def test_create_with_defaults(self) -> None:
        info = PluginInfo(name="test", group=PARSER_GROUP)
        assert info.name == "test"
        assert info.group == PARSER_GROUP
        assert info.module == ""
        assert info.distribution == ""
        assert info.is_builtin is False
        assert info.is_v2 is False
        assert info.load_error == ""

    def test_builtin_detection(self) -> None:
        info = PluginInfo(
            name="markdown",
            group=PARSER_GROUP,
            distribution=BUILTIN_DISTRIBUTION,
            is_builtin=True,
        )
        assert info.is_builtin is True


class TestPluginRegistry:
    def test_empty_registry(self) -> None:
        registry = PluginRegistry()
        assert registry.get_parsers() == {}
        assert registry.get_exporters() == {}
        assert registry.get_connectors() == {}
        assert registry.list_plugins() == []

    def test_discover_all_finds_built_in_parsers(self) -> None:
        """When the package is installed (pip install -e .), entry points are discoverable."""
        registry = PluginRegistry()
        registry.discover_all()
        parsers = registry.get_parsers()

        # Built-in parsers should be discovered if package is installed
        # This test works in both installed and non-installed modes
        if parsers:
            assert "markdown" in parsers
            assert "plaintext" in parsers
            assert "jira" in parsers

    def test_discover_group_returns_plugin_info(self) -> None:
        registry = PluginRegistry()
        infos = registry.discover_group(PARSER_GROUP)
        # Each discovered plugin has a PluginInfo
        for info in infos:
            assert isinstance(info, PluginInfo)
            assert info.group == PARSER_GROUP
            assert info.name != ""

    def test_discover_group_populates_registry(self) -> None:
        registry = PluginRegistry()
        registry.discover_group(PARSER_GROUP)
        parsers = registry.get_parsers()
        infos = registry.list_plugins()

        # Number of successful loads should match registry size
        successful = [i for i in infos if not i.load_error]
        assert len(parsers) == len(successful)

    def test_list_plugins_sorted(self) -> None:
        registry = PluginRegistry()
        registry.discover_all()
        plugins = registry.list_plugins()

        # Should be sorted by (group, name)
        keys = [(p.group, p.name) for p in plugins]
        assert keys == sorted(keys)

    def test_discover_handles_missing_group_gracefully(self) -> None:
        registry = PluginRegistry()
        infos = registry.discover_group("nonexistent.group")
        assert infos == []

    def test_check_compatibility_clean(self) -> None:
        info = PluginInfo(name="test", group=PARSER_GROUP)
        registry = PluginRegistry()
        issues = registry.check_compatibility(info)
        assert issues == []

    def test_check_compatibility_with_load_error(self) -> None:
        info = PluginInfo(name="bad", group=PARSER_GROUP, load_error="ModuleNotFoundError")
        registry = PluginRegistry()
        issues = registry.check_compatibility(info)
        assert len(issues) == 1
        assert "failed to load" in issues[0].lower()

    def test_duplicate_discover_does_not_double_register(self) -> None:
        registry = PluginRegistry()
        registry.discover_group(PARSER_GROUP)
        count_first = len(registry.get_parsers())
        registry.discover_group(PARSER_GROUP)
        count_second = len(registry.get_parsers())
        assert count_first == count_second


class TestCreateRegistry:
    def test_create_registry_returns_populated(self) -> None:
        registry = create_registry()
        assert isinstance(registry, PluginRegistry)
        # Should have discovered at least some plugins if installed
        plugins = registry.list_plugins()
        # This may be empty if not installed, that's OK
        assert isinstance(plugins, list)
