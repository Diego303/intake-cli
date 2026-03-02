"""Tests for the CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

import yaml
from click.testing import CliRunner

from intake.cli import main

if TYPE_CHECKING:
    from pathlib import Path


class TestCLI:
    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "intake" in result.output

    def test_doctor_runs(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["doctor"])
        # May fail due to missing API key but should not crash
        assert result.exit_code in (0, 1)
        assert "Check" in result.output or "PASS" in result.output or "FAIL" in result.output

    def test_init_requires_source(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["init", "test description"])
        assert result.exit_code != 0

    def test_init_missing_source_file(self) -> None:
        """init errors gracefully when source file doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["init", "test project", "-s", "nonexistent.md"],
        )
        assert result.exit_code == 2

    def test_init_dry_run(self, tmp_path: Path) -> None:
        """init --dry-run shows what would be done without creating files."""
        source = tmp_path / "reqs.md"
        source.write_text("# Requirements\nBuild a widget.\n")

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["init", "test project", "-s", str(source), "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_doctor_verbose(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["doctor", "--verbose"])
        assert result.exit_code in (0, 1)

    def test_unknown_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["nonexistent"])
        assert result.exit_code != 0


class TestVerifyCommand:
    def test_verify_runs(self, tmp_path: Path) -> None:
        """verify command loads acceptance.yaml and runs checks."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "acceptance.yaml").write_text(yaml.dump({
            "checks": [
                {
                    "id": "echo",
                    "name": "Echo test",
                    "type": "command",
                    "command": "echo ok",
                    "required": True,
                },
            ],
        }))

        runner = CliRunner()
        result = runner.invoke(
            main, ["verify", str(spec_dir), "-p", str(tmp_path)],
        )
        assert result.exit_code == 0

    def test_verify_json_format(self, tmp_path: Path) -> None:
        """verify --format json outputs JSON."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "acceptance.yaml").write_text(yaml.dump({
            "checks": [
                {
                    "id": "echo",
                    "name": "Echo test",
                    "type": "command",
                    "command": "echo ok",
                    "required": True,
                },
            ],
        }))

        runner = CliRunner()
        result = runner.invoke(
            main, ["verify", str(spec_dir), "-p", str(tmp_path), "-f", "json"],
        )
        assert result.exit_code == 0
        assert '"spec_name"' in result.output

    def test_verify_missing_acceptance(self, tmp_path: Path) -> None:
        """verify errors when acceptance.yaml is missing."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        runner = CliRunner()
        result = runner.invoke(main, ["verify", str(spec_dir)])
        assert result.exit_code == 2


class TestExportCommand:
    def test_export_generic(self, tmp_path: Path) -> None:
        """export -f generic creates SPEC.md and verify.sh."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "requirements.md").write_text("# Requirements\n")
        (spec_dir / "acceptance.yaml").write_text(yaml.dump({"checks": []}))

        output_dir = tmp_path / "out"

        runner = CliRunner()
        result = runner.invoke(
            main, ["export", str(spec_dir), "-f", "generic", "-o", str(output_dir)],
        )
        assert result.exit_code == 0
        assert (output_dir / "SPEC.md").exists()

    def test_export_architect(self, tmp_path: Path) -> None:
        """export -f architect creates pipeline.yaml."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "tasks.md").write_text("# Tasks\n### Task 1: Do thing\n")
        (spec_dir / "acceptance.yaml").write_text(yaml.dump({"checks": []}))

        output_dir = tmp_path / "out"

        runner = CliRunner()
        result = runner.invoke(
            main, ["export", str(spec_dir), "-f", "architect", "-o", str(output_dir)],
        )
        assert result.exit_code == 0
        assert (output_dir / "pipeline.yaml").exists()


class TestShowCommand:
    def test_show_with_lock(self, tmp_path: Path) -> None:
        """show displays spec summary from lock file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "requirements.md").write_text("# Requirements\n")
        (spec_dir / "spec.lock.yaml").write_text(yaml.dump({
            "version": "1",
            "created_at": "2026-03-01T00:00:00",
            "model": "claude-sonnet-4",
            "requirement_count": 5,
            "task_count": 3,
            "total_cost": 0.05,
            "source_hashes": {},
            "spec_hashes": {},
            "config_hash": "",
        }))

        runner = CliRunner()
        result = runner.invoke(main, ["show", str(spec_dir)])
        assert result.exit_code == 0
        assert "claude-sonnet" in result.output

    def test_show_without_lock(self, tmp_path: Path) -> None:
        """show works without a lock file."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "requirements.md").write_text("# Requirements\n")

        runner = CliRunner()
        result = runner.invoke(main, ["show", str(spec_dir)])
        assert result.exit_code == 0
        assert "No spec.lock.yaml" in result.output


class TestListCommand:
    def test_list_no_specs_dir(self, tmp_path: Path) -> None:
        """list shows message when specs directory doesn't exist."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["list", "-d", str(tmp_path / "nonexistent")],
        )
        assert result.exit_code == 0
        assert "No specs directory" in result.output

    def test_list_finds_specs(self, tmp_path: Path) -> None:
        """list finds spec directories."""
        specs_dir = tmp_path / "specs"
        spec1 = specs_dir / "auth"
        spec1.mkdir(parents=True)
        (spec1 / "requirements.md").write_text("# Reqs\n")

        spec2 = specs_dir / "payments"
        spec2.mkdir()
        (spec2 / "acceptance.yaml").write_text("checks: []\n")

        runner = CliRunner()
        result = runner.invoke(main, ["list", "-d", str(specs_dir)])
        assert result.exit_code == 0
        assert "auth" in result.output
        assert "payments" in result.output


class TestDiffCommand:
    def test_diff_shows_changes(self, tmp_path: Path) -> None:
        """diff shows differences between two specs."""
        spec_a = tmp_path / "v1"
        spec_a.mkdir()
        (spec_a / "requirements.md").write_text(
            "# Reqs\n### FR-01: Login\nLogin feature.\n",
        )

        spec_b = tmp_path / "v2"
        spec_b.mkdir()
        (spec_b / "requirements.md").write_text(
            "# Reqs\n### FR-01: Login\nLogin with MFA.\n"
            "### FR-02: Signup\nNew signup.\n",
        )

        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(spec_a), str(spec_b)])
        assert result.exit_code == 0
        assert "FR-02" in result.output

    def test_diff_no_changes(self, tmp_path: Path) -> None:
        """diff reports no changes for identical specs."""
        spec = tmp_path / "v1"
        spec.mkdir()
        (spec / "requirements.md").write_text("# Reqs\n### FR-01: Login\n")

        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(spec), str(spec)])
        assert result.exit_code == 0
        assert "No differences" in result.output
