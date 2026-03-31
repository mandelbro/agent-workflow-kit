"""Integration tests for the full install/update/uninstall lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_workflow_kit.cli.install import install_command, uninstall_command
from claude_workflow_kit.cli.update import update_command
from claude_workflow_kit.core.claude_md import has_managed_section
from claude_workflow_kit.core.manifest import load_manifest
from claude_workflow_kit.core.registry import CORE_ASSETS


@pytest.fixture
def install_dir(tmp_path: Path) -> Path:
    """Provide a clean install directory."""
    return tmp_path / ".claude"


class TestInstallLifecycle:
    """Full lifecycle: install -> verify -> update -> uninstall."""

    def test_fresh_install_creates_all_files(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        for asset in CORE_ASSETS:
            target = install_dir / asset.target_subdir / asset.source.split("/")[-1]
            assert target.exists(), f"Missing: {target}"

    def test_fresh_install_creates_manifest(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        manifest_path = install_dir / ".workflow-kit" / "manifest.json"
        assert manifest_path.exists()

        manifest = load_manifest(manifest_path)
        assert manifest is not None
        assert len(manifest.files) == len(CORE_ASSETS)

    def test_fresh_install_injects_claude_md_section(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        claude_md = install_dir / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert has_managed_section(content)
        assert "Agent Kit Agents" in content
        assert "Agent Kit Workflows" in content
        assert "Agent Kit Guidelines" in content

    def test_install_skip_claude_md(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir, skip_claude_md=True)

        claude_md = install_dir / "CLAUDE.md"
        assert not claude_md.exists()

    def test_install_blocks_without_force(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        # Second install should be a no-op without --force
        install_command(claude_home=install_dir)

        manifest = load_manifest(install_dir / ".workflow-kit" / "manifest.json")
        assert manifest is not None

    def test_install_force_overwrites(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        # Modify a file
        target = install_dir / "agents" / "Norwood.md"
        target.write_text("modified content")

        # Force reinstall
        install_command(claude_home=install_dir, force=True)

        assert target.read_text() != "modified content"

    def test_dry_run_creates_nothing(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir, dry_run=True)

        assert not (install_dir / ".workflow-kit" / "manifest.json").exists()
        assert not (install_dir / "agents" / "Norwood.md").exists()


class TestUpdateLifecycle:
    """Update scenarios after initial install."""

    def test_update_when_not_installed(self, install_dir: Path) -> None:
        # Should not raise
        update_command(claude_home=install_dir)

    def test_update_reports_all_current(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        # Should not raise, all files are current
        update_command(claude_home=install_dir, check_only=True)

    def test_update_detects_missing_files(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        # Remove a file
        target = install_dir / "agents" / "Norwood.md"
        target.unlink()
        assert not target.exists()

        # Update should reinstall it
        update_command(claude_home=install_dir)
        assert target.exists()


class TestUninstallLifecycle:
    """Uninstall scenarios."""

    def test_uninstall_removes_all_files(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        uninstall_command(claude_home=install_dir)

        for asset in CORE_ASSETS:
            target = install_dir / asset.target_subdir / asset.source.split("/")[-1]
            assert not target.exists(), f"Should be removed: {target}"

    def test_uninstall_removes_manifest(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        uninstall_command(claude_home=install_dir)

        assert not (install_dir / ".workflow-kit" / "manifest.json").exists()

    def test_uninstall_removes_claude_md_section(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        claude_md = install_dir / "CLAUDE.md"
        assert has_managed_section(claude_md.read_text())

        uninstall_command(claude_home=install_dir)

        content = claude_md.read_text()
        assert not has_managed_section(content)

    def test_uninstall_keep_files(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        uninstall_command(claude_home=install_dir, keep_files=True)

        # Files should still exist
        target = install_dir / "agents" / "Norwood.md"
        assert target.exists()

        # But manifest should be gone
        assert not (install_dir / ".workflow-kit" / "manifest.json").exists()

    def test_uninstall_when_not_installed(self, install_dir: Path) -> None:
        # Should not raise
        uninstall_command(claude_home=install_dir)

    def test_uninstall_preserves_user_claude_md_content(self, install_dir: Path) -> None:
        # Create user content first
        install_dir.mkdir(parents=True, exist_ok=True)
        claude_md = install_dir / "CLAUDE.md"
        claude_md.write_text("# My Custom Config\n\nUser content here.\n")

        install_command(claude_home=install_dir)
        assert has_managed_section(claude_md.read_text())
        assert "My Custom Config" in claude_md.read_text()

        uninstall_command(claude_home=install_dir)
        content = claude_md.read_text()
        assert "My Custom Config" in content
        assert not has_managed_section(content)


class TestManifestIntegrity:
    """Verify manifest data integrity through operations."""

    def test_manifest_checksums_match_installed_files(self, install_dir: Path) -> None:
        from claude_workflow_kit.core.manifest import file_checksum

        install_command(claude_home=install_dir)
        manifest = load_manifest(install_dir / ".workflow-kit" / "manifest.json")
        assert manifest is not None

        for entry in manifest.files:
            target = Path(entry.target)
            assert target.exists()
            assert file_checksum(target) == entry.checksum

    def test_manifest_json_is_valid(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        manifest_path = install_dir / ".workflow-kit" / "manifest.json"

        data = json.loads(manifest_path.read_text())
        assert "version" in data
        assert "installed_at" in data
        assert "files" in data
        assert isinstance(data["files"], list)
        assert len(data["files"]) == len(CORE_ASSETS)
