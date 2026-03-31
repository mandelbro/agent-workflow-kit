"""Manifest tracking for installed agent-workflow-kit files."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class FileStatus(StrEnum):
    """Status of a managed file relative to what was installed."""

    CURRENT = "current"
    USER_MODIFIED = "user_modified"
    MISSING = "missing"
    OUTDATED = "outdated"


class FileEntry(BaseModel):
    """A single file tracked by the manifest."""

    source: str  # relative path within bundled assets (e.g. "agents/Norwood.md")
    target: str  # absolute path where installed (e.g. "~/.claude/agents/Norwood.md")
    checksum: str  # sha256 hex digest at install time
    installed_at: str  # ISO 8601 timestamp


class Manifest(BaseModel):
    """Root manifest model."""

    version: str = "0.1.0"
    installed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    files: list[FileEntry] = Field(default_factory=lambda: [])


def file_checksum(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_file_status(entry: FileEntry) -> FileStatus:
    """Check the current status of a managed file against its manifest entry."""
    target = Path(entry.target).expanduser()
    if not target.exists():
        return FileStatus.MISSING
    current_hash = file_checksum(target)
    if current_hash == entry.checksum:
        return FileStatus.CURRENT
    return FileStatus.USER_MODIFIED


def load_manifest(path: Path) -> Manifest | None:
    """Load manifest from disk, returning None if it doesn't exist."""
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Manifest.model_validate(data)


def save_manifest(manifest: Manifest, path: Path) -> None:
    """Write manifest to disk atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    tmp.rename(path)
