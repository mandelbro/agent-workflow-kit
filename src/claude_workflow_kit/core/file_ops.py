"""File operations for agent-workflow-kit: copy, backup, atomic write."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)


def backup_file(path: Path) -> Path | None:
    """Create a timestamped backup of a file. Returns backup path, or None if file doesn't exist."""
    if not path.exists():
        return None
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    backup_path = path.with_suffix(f".{timestamp}.bak")
    shutil.copy2(path, backup_path)
    return backup_path


def copy_file(source: Path, target: Path, *, create_backup: bool = True) -> Path | None:
    """Copy source to target, optionally backing up the target first.

    Returns the backup path if a backup was created, None otherwise.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    backup_path = None
    if create_backup and target.exists():
        backup_path = backup_file(target)
    shutil.copy2(source, target)
    return backup_path


def remove_file(path: Path) -> bool:
    """Remove a file if it exists. Returns True if removed, False if it didn't exist."""
    if path.exists():
        path.unlink()
        return True
    return False
