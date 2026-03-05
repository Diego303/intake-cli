"""Tests for the SpecWatcher file watcher."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from intake.config.schema import WatchConfig
from intake.watch import WatchError


@pytest.fixture()
def watch_config() -> WatchConfig:
    """Default watch configuration for tests."""
    return WatchConfig(
        debounce_seconds=0.5,
        ignore_patterns=["*.pyc", "__pycache__", ".git"],
    )


@pytest.fixture()
def spec_with_acceptance(tmp_path: Path) -> Path:
    """Create a spec directory with acceptance.yaml."""
    spec = tmp_path / "specs" / "test-spec"
    spec.mkdir(parents=True)

    (spec / "acceptance.yaml").write_text(
        yaml.dump(
            {
                "checks": [
                    {
                        "id": "check-1",
                        "name": "README exists",
                        "type": "files_exist",
                        "paths": ["README.md"],
                        "required": True,
                    },
                    {
                        "id": "check-2",
                        "name": "src dir exists",
                        "type": "files_exist",
                        "paths": ["src/"],
                        "required": False,
                    },
                ]
            }
        )
    )
    (spec / "tasks.md").write_text("# Tasks\n\n## Task 1: Setup\n\n**Status:** pending\n")
    return spec


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a project directory with some files."""
    project = tmp_path / "project"
    project.mkdir()
    (project / "README.md").write_text("# Test Project")
    return project


class TestSpecWatcherInit:
    """Tests for SpecWatcher initialization."""

    def test_creates_watcher(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        assert watcher.spec_dir == spec_with_acceptance
        assert watcher.project_dir == project_dir
        assert watcher.last_report is None

    def test_creates_watcher_with_tags(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
            tags=["test", "lint"],
        )
        assert watcher.tags == ["test", "lint"]

    def test_default_tags_is_none(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        assert watcher.tags is None

    def test_acceptance_file_path(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        assert watcher._acceptance_file.endswith("acceptance.yaml")

    def test_engine_initialized(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        assert watcher.engine is not None


class TestSpecWatcherRunOnce:
    """Tests for run_once (single verification without watching)."""

    def test_run_once_with_passing_checks(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        report = watcher.run_once()
        # README.md exists in project_dir, so check-1 should pass
        assert report.passed >= 1
        assert watcher.last_report is not None

    def test_run_once_with_failing_checks(
        self,
        spec_with_acceptance: Path,
        tmp_path: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        # Empty project dir without README
        empty_project = tmp_path / "empty-proj"
        empty_project.mkdir()

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(empty_project),
            config=watch_config,
        )
        report = watcher.run_once()
        # check-1 (README exists) should fail
        assert report.failed >= 1
        assert not report.all_required_passed

    def test_run_once_updates_last_report(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        assert watcher.last_report is None
        report = watcher.run_once()
        assert watcher.last_report is report

    def test_run_once_returns_verification_report(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.verify.engine import VerificationReport
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        report = watcher.run_once()
        assert isinstance(report, VerificationReport)


class TestSpecWatcherFiltering:
    """Tests for ignore pattern filtering."""

    def test_filter_ignored_files(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        files = [
            "src/main.py",
            "src/__pycache__/cache.pyc",
            "tests/test.py",
            ".git/objects/abc",
            "build/output.pyc",
        ]
        result = watcher._filter_ignored(files, watch_config.ignore_patterns)
        assert "src/main.py" in result
        assert "tests/test.py" in result
        # These should be filtered out
        assert "src/__pycache__/cache.pyc" not in result
        assert ".git/objects/abc" not in result
        assert "build/output.pyc" not in result

    def test_filter_with_no_patterns(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        config = WatchConfig(ignore_patterns=[])
        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=config,
        )
        files = ["a.py", "b.pyc", ".git/x"]
        result = watcher._filter_ignored(files, [])
        assert len(result) == 3

    def test_filter_preserves_order(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        files = ["c.py", "b.py", "a.py"]
        result = watcher._filter_ignored(files, [])
        assert result == ["c.py", "b.py", "a.py"]

    def test_filter_git_nested_paths(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        files = [
            ".git/HEAD",
            ".git/objects/pack/pack-abc.idx",
            ".git/refs/heads/main",
        ]
        result = watcher._filter_ignored(files, [".git"])
        assert len(result) == 0

    def test_filter_pycache_nested(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        files = [
            "src/__pycache__/module.cpython-312.pyc",
            "tests/__pycache__/conftest.cpython-312.pyc",
        ]
        result = watcher._filter_ignored(files, ["__pycache__", "*.pyc"])
        assert len(result) == 0

    def test_matches_any_with_exact_file(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        assert SpecWatcher._matches_any("test.pyc", ["*.pyc"])
        assert not SpecWatcher._matches_any("test.py", ["*.pyc"])

    def test_matches_any_with_directory_component(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        assert SpecWatcher._matches_any(".git/objects/abc", [".git"])
        assert SpecWatcher._matches_any("path/to/__pycache__/file.pyc", ["__pycache__"])
        assert not SpecWatcher._matches_any("src/main.py", [".git"])


class TestSpecWatcherChangeExtraction:
    """Tests for _extract_changed_files."""

    def test_extract_changes(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        changes = {
            (1, str(project_dir / "src" / "main.py")),
            (2, str(project_dir / "README.md")),
        }
        result = watcher._extract_changed_files(changes)
        # Should get relative paths
        assert len(result) == 2
        paths = set(result)
        assert "README.md" in paths or str(Path("src/main.py")) in paths

    def test_extract_changes_outside_project(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        changes = {
            (1, "/some/absolute/path/outside/project.py"),
        }
        result = watcher._extract_changed_files(changes)
        # Should fall back to absolute path
        assert len(result) == 1
        assert "/some/absolute/path/outside/project.py" in result[0]

    def test_extract_empty_changes(
        self,
        spec_with_acceptance: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(spec_with_acceptance),
            project_dir=str(project_dir),
            config=watch_config,
        )
        result = watcher._extract_changed_files(set())
        assert result == []


class TestSpecWatcherRunValidation:
    """Tests for run() validation."""

    def test_run_missing_spec_dir(
        self,
        tmp_path: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        watcher = SpecWatcher(
            spec_dir=str(tmp_path / "nonexistent"),
            project_dir=str(project_dir),
            config=watch_config,
        )
        with pytest.raises((WatchError, ImportError)):
            watcher.run()

    def test_run_missing_acceptance_yaml(
        self,
        tmp_path: Path,
        project_dir: Path,
        watch_config: WatchConfig,
    ) -> None:
        from intake.watch.watcher import SpecWatcher

        # Spec dir exists but no acceptance.yaml
        spec = tmp_path / "empty-spec"
        spec.mkdir()

        watcher = SpecWatcher(
            spec_dir=str(spec),
            project_dir=str(project_dir),
            config=watch_config,
        )
        with pytest.raises((WatchError, ImportError)):
            watcher.run()


class TestWatchConfig:
    """Tests for WatchConfig defaults."""

    def test_default_values(self) -> None:
        config = WatchConfig()
        assert config.debounce_seconds == 2.0
        assert "*.pyc" in config.ignore_patterns
        assert "__pycache__" in config.ignore_patterns
        assert ".git" in config.ignore_patterns
        assert "node_modules" in config.ignore_patterns
        assert ".intake" in config.ignore_patterns

    def test_custom_values(self) -> None:
        config = WatchConfig(
            debounce_seconds=5.0,
            ignore_patterns=["*.log"],
        )
        assert config.debounce_seconds == 5.0
        assert config.ignore_patterns == ["*.log"]


class TestWatchError:
    """Tests for WatchError exception."""

    def test_error_with_reason(self) -> None:
        err = WatchError("something went wrong")
        assert "something went wrong" in str(err)
        assert err.reason == "something went wrong"
        assert err.suggestion == ""

    def test_error_with_suggestion(self) -> None:
        err = WatchError("missing file", suggestion="run intake init")
        assert "missing file" in str(err)
        assert "run intake init" in str(err)

    def test_error_is_exception(self) -> None:
        err = WatchError("test")
        assert isinstance(err, Exception)


class TestMaxChangedFilesDisplay:
    """Tests for the MAX_CHANGED_FILES_DISPLAY constant."""

    def test_constant_exists(self) -> None:
        from intake.watch.watcher import MAX_CHANGED_FILES_DISPLAY

        assert isinstance(MAX_CHANGED_FILES_DISPLAY, int)
        assert MAX_CHANGED_FILES_DISPLAY > 0
