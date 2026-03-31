"""Tests for core.file_ops: atomic writes, backups, copies, removal."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from claude_workflow_kit.core.file_ops import (
    atomic_write,
    backup_file,
    copy_file,
    remove_file,
)

# --- atomic_write ---


class TestAtomicWrite:
    def test_creates_file_with_correct_content(self, tmp_path: Path) -> None:
        target = tmp_path / "output.txt"
        atomic_write(target, "hello world")

        assert target.read_text(encoding="utf-8") == "hello world"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "deep" / "file.md"
        atomic_write(target, "# Title")

        assert target.exists()
        assert target.read_text(encoding="utf-8") == "# Title"

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "existing.txt"
        target.write_text("old content", encoding="utf-8")

        atomic_write(target, "new content")

        assert target.read_text(encoding="utf-8") == "new content"

    def test_no_temp_file_remains(self, tmp_path: Path) -> None:
        target = tmp_path / "clean.txt"
        atomic_write(target, "data")

        remaining = list(tmp_path.iterdir())
        assert remaining == [target]


# --- backup_file ---


class TestBackupFile:
    def test_creates_bak_with_original_content(self, tmp_path: Path) -> None:
        original = tmp_path / "config.json"
        original.write_text('{"key": "value"}', encoding="utf-8")

        bak = backup_file(original)

        assert bak is not None
        assert bak.read_text(encoding="utf-8") == '{"key": "value"}'

    def test_returns_none_for_nonexistent_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.txt"

        assert backup_file(missing) is None

    def test_backup_filename_contains_timestamp(self, tmp_path: Path) -> None:
        original = tmp_path / "data.yml"
        original.write_text("content", encoding="utf-8")

        bak = backup_file(original)

        assert bak is not None
        # Expected pattern: data.YYYYMMDDTHHMMSS.bak
        assert re.search(r"\.\d{8}T\d{6}\.bak$", bak.name)

    def test_original_file_unchanged(self, tmp_path: Path) -> None:
        original = tmp_path / "keep.txt"
        original.write_text("preserve me", encoding="utf-8")

        backup_file(original)

        assert original.read_text(encoding="utf-8") == "preserve me"


# --- copy_file ---


class TestCopyFile:
    def test_copies_content_correctly(self, tmp_path: Path) -> None:
        source = tmp_path / "src.txt"
        source.write_text("payload", encoding="utf-8")
        target = tmp_path / "dst.txt"

        copy_file(source, target)

        assert target.read_text(encoding="utf-8") == "payload"

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        source = tmp_path / "src.md"
        source.write_text("# Doc", encoding="utf-8")
        target = tmp_path / "a" / "b" / "dst.md"

        copy_file(source, target)

        assert target.exists()
        assert target.read_text(encoding="utf-8") == "# Doc"

    def test_creates_backup_of_existing_target(self, tmp_path: Path) -> None:
        source = tmp_path / "new.txt"
        source.write_text("new data", encoding="utf-8")
        target = tmp_path / "existing.txt"
        target.write_text("old data", encoding="utf-8")

        bak = copy_file(source, target, create_backup=True)

        assert bak is not None
        assert bak.read_text(encoding="utf-8") == "old data"
        assert target.read_text(encoding="utf-8") == "new data"

    def test_skips_backup_when_disabled(self, tmp_path: Path) -> None:
        source = tmp_path / "new.txt"
        source.write_text("new data", encoding="utf-8")
        target = tmp_path / "existing.txt"
        target.write_text("old data", encoding="utf-8")

        bak = copy_file(source, target, create_backup=False)

        assert bak is None
        assert target.read_text(encoding="utf-8") == "new data"

    def test_returns_none_when_target_does_not_exist(self, tmp_path: Path) -> None:
        source = tmp_path / "src.txt"
        source.write_text("content", encoding="utf-8")
        target = tmp_path / "brand_new.txt"

        bak = copy_file(source, target)

        assert bak is None
        assert target.read_text(encoding="utf-8") == "content"


# --- remove_file ---


class TestRemoveFile:
    def test_removes_existing_file(self, tmp_path: Path) -> None:
        victim = tmp_path / "delete_me.txt"
        victim.write_text("bye", encoding="utf-8")

        result = remove_file(victim)

        assert result is True
        assert not victim.exists()

    def test_returns_false_for_nonexistent_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "ghost.txt"

        result = remove_file(missing)

        assert result is False
