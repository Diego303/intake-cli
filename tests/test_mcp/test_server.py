"""Tests for MCP server creation (without requiring the mcp package)."""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestCreateServer:
    """Tests for create_server function."""

    def test_import_error_when_mcp_not_installed(self) -> None:
        """Verify clear error message when mcp package is missing."""
        with (
            patch.dict("sys.modules", {"mcp": None, "mcp.server": None}),
            pytest.raises(ImportError, match="mcp package"),
        ):
            # Force reimport
            import importlib

            import intake.mcp.server

            importlib.reload(intake.mcp.server)
            intake.mcp.server.create_server()


class TestMCPServerConstants:
    """Tests for server constants."""

    def test_server_name(self) -> None:
        from intake.mcp.server import MCP_SERVER_NAME

        assert MCP_SERVER_NAME == "intake-spec"

    def test_server_name_is_string(self) -> None:
        from intake.mcp.server import MCP_SERVER_NAME

        assert isinstance(MCP_SERVER_NAME, str)


class TestMCPError:
    """Test MCPError with and without suggestion."""

    def test_error_with_reason(self) -> None:
        from intake.mcp import MCPError

        err = MCPError("test error")
        assert "test error" in str(err)
        assert err.reason == "test error"
        assert err.suggestion == ""

    def test_error_with_suggestion(self) -> None:
        from intake.mcp import MCPError

        err_with_hint = MCPError("bad thing", suggestion="try this")
        assert "bad thing" in str(err_with_hint)
        assert "try this" in str(err_with_hint)

    def test_error_is_exception(self) -> None:
        from intake.mcp import MCPError

        err = MCPError("test")
        assert isinstance(err, Exception)


class TestModuleExports:
    """Tests for __init__.py exports."""

    def test_all_exports(self) -> None:
        from intake.mcp import __all__

        assert "MCPError" in __all__
        assert "create_server" in __all__
        assert "run_stdio" in __all__
        assert "run_sse" in __all__

    def test_create_server_importable(self) -> None:
        from intake.mcp import create_server

        assert callable(create_server)

    def test_run_stdio_importable(self) -> None:
        from intake.mcp import run_stdio

        assert callable(run_stdio)

    def test_run_sse_importable(self) -> None:
        from intake.mcp import run_sse

        assert callable(run_sse)
