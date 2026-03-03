"""Tests for generate/lock.py — spec lock generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from intake.generate.lock import SpecLock, _hash_file, create_lock

if TYPE_CHECKING:
    from pathlib import Path


class TestHashFile:
    """Tests for _hash_file()."""

    def test_returns_16_char_hex(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        result = _hash_file(str(f))
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("content A")
        f2.write_text("content B")
        assert _hash_file(str(f1)) != _hash_file(str(f2))

    def test_same_content_same_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("same content")
        f2.write_text("same content")
        assert _hash_file(str(f1)) == _hash_file(str(f2))


class TestSpecLock:
    """Tests for SpecLock dataclass."""

    def test_to_yaml_and_from_yaml(self, tmp_path: Path) -> None:
        lock = SpecLock(
            version="1",
            created_at="2026-01-01T00:00:00+00:00",
            model="claude-sonnet-4",
            total_cost=0.05,
            requirement_count=5,
            task_count=3,
        )
        lock_path = str(tmp_path / "spec.lock.yaml")
        lock.to_yaml(lock_path)

        loaded = SpecLock.from_yaml(lock_path)
        assert loaded.version == "1"
        assert loaded.model == "claude-sonnet-4"
        assert loaded.total_cost == 0.05
        assert loaded.requirement_count == 5
        assert loaded.task_count == 3

    def test_is_stale_detects_changed_source(self, tmp_path: Path) -> None:
        source = tmp_path / "reqs.md"
        source.write_text("original content")

        lock = SpecLock(source_hashes={str(source): _hash_file(str(source))})

        # Not stale before change
        assert lock.is_stale([str(source)]) is False

        # Stale after change
        source.write_text("modified content")
        assert lock.is_stale([str(source)]) is True

    def test_is_stale_detects_missing_source(self, tmp_path: Path) -> None:
        lock = SpecLock(source_hashes={})
        fake_source = tmp_path / "new.md"
        fake_source.write_text("new")
        assert lock.is_stale([str(fake_source)]) is True

    def test_is_stale_returns_false_when_all_match(self, tmp_path: Path) -> None:
        source = tmp_path / "reqs.md"
        source.write_text("content")
        lock = SpecLock(source_hashes={str(source): _hash_file(str(source))})
        assert lock.is_stale([str(source)]) is False


class TestCreateLock:
    """Tests for create_lock()."""

    def test_creates_lock_with_source_hashes(self, tmp_path: Path) -> None:
        source = tmp_path / "reqs.md"
        source.write_text("requirements")
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "requirements.md").write_text("# Reqs")

        lock = create_lock(
            sources=[str(source)],
            spec_dir=str(spec_dir),
            model="test-model",
            total_cost=0.1,
            requirement_count=5,
            task_count=3,
        )

        assert str(source) in lock.source_hashes
        assert "requirements.md" in lock.spec_hashes
        assert lock.model == "test-model"
        assert lock.total_cost == 0.1
        assert lock.requirement_count == 5
        assert lock.task_count == 3
        assert lock.created_at != ""

    def test_skips_nonexistent_sources(self, tmp_path: Path) -> None:
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        lock = create_lock(
            sources=["/nonexistent/file.md"],
            spec_dir=str(spec_dir),
            model="test-model",
            total_cost=0.0,
            requirement_count=0,
            task_count=0,
        )

        assert len(lock.source_hashes) == 0

    def test_excludes_lock_file_from_spec_hashes(self, tmp_path: Path) -> None:
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        (spec_dir / "requirements.md").write_text("# Reqs")
        (spec_dir / "spec.lock.yaml").write_text("version: 1")

        lock = create_lock(
            sources=[],
            spec_dir=str(spec_dir),
            model="test-model",
            total_cost=0.0,
            requirement_count=0,
            task_count=0,
        )

        assert "requirements.md" in lock.spec_hashes
        assert "spec.lock.yaml" not in lock.spec_hashes
