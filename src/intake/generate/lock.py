"""Spec lock generation for reproducibility.

Records source hashes, spec hashes, model, cost, and timestamps
so that spec staleness can be detected.
"""

from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger()

LOCK_FILENAME = "spec.lock.yaml"


@dataclass
class SpecLock:
    """Pins the state of a spec for reproducibility.

    Records:
    - Hash of each source file used
    - Hash of each generated spec file
    - Model and config used for analysis
    - Timestamp
    - Cost and counts
    """

    version: str = "1"
    created_at: str = ""
    model: str = ""
    config_hash: str = ""
    source_hashes: dict[str, str] = field(default_factory=dict)
    spec_hashes: dict[str, str] = field(default_factory=dict)
    total_cost: float = 0.0
    requirement_count: int = 0
    task_count: int = 0

    def is_stale(self, sources: list[str]) -> bool:
        """Check if any source has changed since the lock was created.

        Args:
            sources: List of source file paths to check.

        Returns:
            True if any source has changed or is missing from the lock.
        """
        for source in sources:
            current_hash = _hash_file(source)
            locked_hash = self.source_hashes.get(source)
            if locked_hash is None or current_hash != locked_hash:
                return True
        return False

    def to_yaml(self, path: str) -> None:
        """Write lock file to disk.

        Args:
            path: Output file path.
        """
        data = dataclasses.asdict(self)
        Path(path).write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        logger.info("lock_written", path=path)

    @classmethod
    def from_yaml(cls, path: str) -> SpecLock:
        """Load lock file from disk.

        Args:
            path: Path to an existing lock file.

        Returns:
            Loaded SpecLock instance.
        """
        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            return cls()
        return cls(**data)


def create_lock(
    sources: list[str],
    spec_dir: str,
    model: str,
    total_cost: float,
    requirement_count: int,
    task_count: int,
) -> SpecLock:
    """Create a lock for the current spec state.

    Args:
        sources: List of source file paths.
        spec_dir: Directory containing the generated spec files.
        model: LLM model identifier used for analysis.
        total_cost: Total LLM cost for this spec generation.
        requirement_count: Total number of requirements.
        task_count: Total number of implementation tasks.

    Returns:
        A SpecLock populated with hashes and metadata.
    """
    lock = SpecLock(
        created_at=datetime.now(UTC).isoformat(),
        model=model,
        total_cost=total_cost,
        requirement_count=requirement_count,
        task_count=task_count,
    )

    for source in sources:
        source_path = Path(source)
        if source_path.exists():
            lock.source_hashes[source] = _hash_file(source)

    spec_path = Path(spec_dir)
    if spec_path.exists():
        for f in sorted(spec_path.iterdir()):
            if f.is_file() and f.name != LOCK_FILENAME:
                lock.spec_hashes[f.name] = _hash_file(str(f))

    logger.info(
        "lock_created",
        sources=len(lock.source_hashes),
        spec_files=len(lock.spec_hashes),
        model=model,
    )

    return lock


def _hash_file(path: str) -> str:
    """SHA-256 hash of a file (first 16 hex chars).

    Args:
        path: Path to the file.

    Returns:
        First 16 characters of the hex digest.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]
