"""Tests for CLI commands via Typer CliRunner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from claude_workflow_kit.cli.app import app
from claude_workflow_kit.cli.install import install_command

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


@pytest.fixture
def installed_dir(tmp_path: Path) -> Path:
    """Install into a temp directory and return the path."""
    home = tmp_path / ".claude"
    install_command(claude_home=home)
    return home


class TestInstallCLI:
    def test_install_via_cli(self, tmp_path: Path) -> None:
        home = tmp_path / ".claude"
        result = runner.invoke(app, ["install", "--claude-home", str(home)])
        assert result.exit_code == 0
        assert "Installation complete" in result.output

    def test_install_dry_run(self, tmp_path: Path) -> None:
        home = tmp_path / ".claude"
        result = runner.invoke(app, ["install", "--claude-home", str(home), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert not (home / ".workflow-kit" / "manifest.json").exists()

    def test_install_already_installed(self, installed_dir: Path) -> None:
        result = runner.invoke(app, ["install", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert "already installed" in result.output

    def test_install_force(self, installed_dir: Path) -> None:
        result = runner.invoke(app, ["install", "--claude-home", str(installed_dir), "--force"])
        assert result.exit_code == 0
        assert "Installation complete" in result.output

    def test_install_skip_claude_md(self, tmp_path: Path) -> None:
        home = tmp_path / ".claude"
        result = runner.invoke(app, ["install", "--claude-home", str(home), "--skip-claude-md"])
        assert result.exit_code == 0
        assert not (home / "CLAUDE.md").exists()


class TestUninstallCLI:
    def test_uninstall_via_cli(self, installed_dir: Path) -> None:
        result = runner.invoke(app, ["uninstall", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert "Uninstall complete" in result.output

    def test_uninstall_not_installed(self, tmp_path: Path) -> None:
        home = tmp_path / ".claude"
        result = runner.invoke(app, ["uninstall", "--claude-home", str(home)])
        assert result.exit_code == 0
        assert "not installed" in result.output

    def test_uninstall_keep_files(self, installed_dir: Path) -> None:
        result = runner.invoke(
            app, ["uninstall", "--claude-home", str(installed_dir), "--keep-files"]
        )
        assert result.exit_code == 0
        assert (installed_dir / "agents" / "Norwood.md").exists()

    def test_uninstall_dry_run(self, installed_dir: Path) -> None:
        result = runner.invoke(app, ["uninstall", "--claude-home", str(installed_dir), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert (installed_dir / ".workflow-kit" / "manifest.json").exists()


class TestStatusCLI:
    def test_status_when_installed(self, installed_dir: Path) -> None:
        result = runner.invoke(app, ["status", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert "current" in result.output
        assert "Version: 0.1.0" in result.output

    def test_status_not_installed(self, tmp_path: Path) -> None:
        home = tmp_path / ".claude"
        result = runner.invoke(app, ["status", "--claude-home", str(home)])
        assert result.exit_code == 0
        assert "not installed" in result.output


class TestListCLI:
    def test_list_all(self) -> None:
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Norwood.md" in result.output
        assert "tasks-workflow.md" in result.output
        assert "testing-strategy.md" in result.output

    def test_list_agents(self) -> None:
        result = runner.invoke(app, ["list", "agents"])
        assert result.exit_code == 0
        assert "Norwood.md" in result.output

    def test_list_workflows(self) -> None:
        result = runner.invoke(app, ["list", "workflows"])
        assert result.exit_code == 0
        assert "tasks-workflow.md" in result.output

    def test_list_guidelines(self) -> None:
        result = runner.invoke(app, ["list", "guidelines"])
        assert result.exit_code == 0
        assert "testing-strategy.md" in result.output

    def test_list_invalid_category(self) -> None:
        result = runner.invoke(app, ["list", "bogus"])
        assert result.exit_code == 0
        assert "Unknown category" in result.output


class TestDoctorCLI:
    def test_doctor_healthy(self, installed_dir: Path) -> None:
        result = runner.invoke(app, ["doctor", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert "checks passed" in result.output
        assert "healthy" in result.output

    def test_doctor_not_installed(self, tmp_path: Path) -> None:
        home = tmp_path / ".claude"
        home.mkdir(parents=True)
        result = runner.invoke(app, ["doctor", "--claude-home", str(home)])
        assert result.exit_code == 0
        assert "FAIL" in result.output

    def test_doctor_missing_file(self, installed_dir: Path) -> None:
        (installed_dir / "agents" / "Norwood.md").unlink()
        result = runner.invoke(app, ["doctor", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert "issue" in result.output


class TestUpdateCLI:
    def test_update_all_current(self, installed_dir: Path) -> None:
        result = runner.invoke(app, ["update", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_update_not_installed(self, tmp_path: Path) -> None:
        home = tmp_path / ".claude"
        result = runner.invoke(app, ["update", "--claude-home", str(home)])
        assert result.exit_code == 0
        assert "not installed" in result.output

    def test_update_check_only(self, installed_dir: Path) -> None:
        result = runner.invoke(app, ["update", "--claude-home", str(installed_dir), "--check-only"])
        assert result.exit_code == 0
        assert "up to date" in result.output

    def test_update_missing_file_restored(self, installed_dir: Path) -> None:
        target = installed_dir / "agents" / "Norwood.md"
        target.unlink()
        result = runner.invoke(app, ["update", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert target.exists()

    def test_update_user_modified_skipped(self, installed_dir: Path) -> None:
        target = installed_dir / "agents" / "Norwood.md"
        target.write_text("user edits")
        result = runner.invoke(app, ["update", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert target.read_text() == "user edits"

    def test_update_user_modified_no_upstream_change(self, installed_dir: Path) -> None:
        target = installed_dir / "agents" / "Norwood.md"
        target.write_text("user edits")
        result = runner.invoke(app, ["update", "--claude-home", str(installed_dir)])
        assert result.exit_code == 0
        assert "user modified" in result.output
        assert target.read_text() == "user edits"


class TestDiffCLI:
    def test_diff_no_changes(self, installed_dir: Path) -> None:
        result = runner.invoke(
            app, ["diff", "agents/Norwood.md", "--claude-home", str(installed_dir)]
        )
        assert result.exit_code == 0
        assert "No differences" in result.output

    def test_diff_with_changes(self, installed_dir: Path) -> None:
        target = installed_dir / "agents" / "Norwood.md"
        target.write_text("modified content\n")
        result = runner.invoke(
            app, ["diff", "agents/Norwood.md", "--claude-home", str(installed_dir)]
        )
        assert result.exit_code == 0
        assert "Diff" in result.output

    def test_diff_unknown_file(self, installed_dir: Path) -> None:
        result = runner.invoke(
            app, ["diff", "agents/Bogus.md", "--claude-home", str(installed_dir)]
        )
        assert result.exit_code == 0
        assert "not managed" in result.output

    def test_diff_not_installed(self, tmp_path: Path) -> None:
        home = tmp_path / ".claude"
        result = runner.invoke(app, ["diff", "agents/Norwood.md", "--claude-home", str(home)])
        assert result.exit_code == 0
        assert "not installed" in result.output
