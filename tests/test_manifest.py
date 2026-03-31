"""Tests for the manifest tracking module."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from claude_workflow_kit.core.manifest import (
    FileEntry,
    FileStatus,
    Manifest,
    check_file_status,
    file_checksum,
    load_manifest,
    save_manifest,
)


class TestFileChecksum:
    """Tests for file_checksum."""

    def test_produces_correct_sha256(self, tmp_path: Path) -> None:
        content = b"hello, manifest"
        target = tmp_path / "sample.txt"
        target.write_bytes(content)

        expected = hashlib.sha256(content).hexdigest()
        assert file_checksum(target) == expected

    def test_empty_file_checksum(self, tmp_path: Path) -> None:
        target = tmp_path / "empty.txt"
        target.write_bytes(b"")

        expected = hashlib.sha256(b"").hexdigest()
        assert file_checksum(target) == expected


class TestFileEntry:
    """Tests for the FileEntry model."""

    def test_validates_correctly(self) -> None:
        entry = FileEntry(
            source="agents/Norwood.md",
            target="~/.claude/agents/Norwood.md",
            checksum="abc123",
            installed_at="2025-01-01T00:00:00+00:00",
        )
        assert entry.source == "agents/Norwood.md"
        assert entry.target == "~/.claude/agents/Norwood.md"
        assert entry.checksum == "abc123"
        assert entry.installed_at == "2025-01-01T00:00:00+00:00"

    def test_round_trips_through_json(self) -> None:
        entry = FileEntry(
            source="workflows/tdd.md",
            target="/home/user/.claude/workflows/tdd.md",
            checksum="deadbeef",
            installed_at="2025-06-15T12:00:00+00:00",
        )
        data = json.loads(entry.model_dump_json())
        restored = FileEntry.model_validate(data)
        assert restored == entry


class TestManifest:
    """Tests for the Manifest model."""

    def test_has_correct_defaults(self) -> None:
        manifest = Manifest()
        assert manifest.version == "0.1.0"
        assert manifest.installed_at  # non-empty ISO timestamp
        assert manifest.files == []

    def test_installed_at_is_iso_format(self) -> None:
        manifest = Manifest()
        # Should not raise if it's valid ISO 8601
        from datetime import datetime

        datetime.fromisoformat(manifest.installed_at)


class TestCheckFileStatus:
    """Tests for check_file_status."""

    def test_returns_missing_when_file_does_not_exist(self, tmp_path: Path) -> None:
        entry = FileEntry(
            source="agents/Ghost.md",
            target=str(tmp_path / "nonexistent.md"),
            checksum="irrelevant",
            installed_at="2025-01-01T00:00:00+00:00",
        )
        assert check_file_status(entry) == FileStatus.MISSING

    def test_returns_current_when_checksum_matches(self, tmp_path: Path) -> None:
        content = b"matching content"
        target = tmp_path / "agent.md"
        target.write_bytes(content)
        checksum = hashlib.sha256(content).hexdigest()

        entry = FileEntry(
            source="agents/agent.md",
            target=str(target),
            checksum=checksum,
            installed_at="2025-01-01T00:00:00+00:00",
        )
        assert check_file_status(entry) == FileStatus.CURRENT

    def test_returns_user_modified_when_checksum_differs(self, tmp_path: Path) -> None:
        target = tmp_path / "modified.md"
        target.write_bytes(b"original content")
        original_checksum = hashlib.sha256(b"original content").hexdigest()

        # Modify the file after recording the entry
        target.write_bytes(b"user edited this")

        entry = FileEntry(
            source="agents/modified.md",
            target=str(target),
            checksum=original_checksum,
            installed_at="2025-01-01T00:00:00+00:00",
        )
        assert check_file_status(entry) == FileStatus.USER_MODIFIED


class TestSaveAndLoadManifest:
    """Tests for save_manifest and load_manifest."""

    def test_save_writes_valid_json(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "state" / "manifest.json"
        manifest = Manifest(version="0.1.0", files=[])
        save_manifest(manifest, manifest_path)

        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert raw["version"] == "0.1.0"
        assert isinstance(raw["files"], list)

    def test_load_returns_none_for_nonexistent_path(self, tmp_path: Path) -> None:
        result = load_manifest(tmp_path / "does_not_exist.json")
        assert result is None

    def test_load_reads_saved_manifest(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        manifest = Manifest(
            version="0.1.0",
            installed_at="2025-03-01T00:00:00+00:00",
            files=[
                FileEntry(
                    source="agents/Ada.md",
                    target="/home/user/.claude/agents/Ada.md",
                    checksum="abc123def456",
                    installed_at="2025-03-01T00:00:00+00:00",
                )
            ],
        )
        save_manifest(manifest, manifest_path)
        loaded = load_manifest(manifest_path)

        assert loaded is not None
        assert loaded.version == manifest.version
        assert loaded.installed_at == manifest.installed_at
        assert len(loaded.files) == 1
        assert loaded.files[0].source == "agents/Ada.md"

    def test_round_trip_preserves_all_data(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "roundtrip" / "manifest.json"
        entries = [
            FileEntry(
                source=f"agents/agent{i}.md",
                target=f"/home/user/.claude/agents/agent{i}.md",
                checksum=hashlib.sha256(f"content{i}".encode()).hexdigest(),
                installed_at="2025-06-01T10:00:00+00:00",
            )
            for i in range(3)
        ]
        original = Manifest(
            version="0.1.0",
            installed_at="2025-06-01T10:00:00+00:00",
            files=entries,
        )

        save_manifest(original, manifest_path)
        restored = load_manifest(manifest_path)

        assert restored is not None
        assert restored == original

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        deep_path = tmp_path / "a" / "b" / "c" / "manifest.json"
        manifest = Manifest()
        save_manifest(manifest, deep_path)
        assert deep_path.exists()
