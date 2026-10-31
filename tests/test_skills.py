"""Tests for skill assets (directories under CLAUDE_HOME/skills/)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from claude_workflow_kit.cli.app import app
from claude_workflow_kit.cli.install import install_command, uninstall_command
from claude_workflow_kit.cli.update import update_command
from claude_workflow_kit.core.manifest import load_manifest
from claude_workflow_kit.core.registry import (
    CORE_ASSETS,
    get_assets_by_category,
    get_assets_dir,
)

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()

SKILL_FILES = ("SKILL.md", "outcome.schema.json", "worked-example.md")


@pytest.fixture
def install_dir(tmp_path: Path) -> Path:
    return tmp_path / ".claude"


@pytest.fixture
def skill_md() -> str:
    return (get_assets_dir() / "skills" / "tdd-pair" / "SKILL.md").read_text()


class TestRegistry:
    def test_tdd_pair_files_are_registered_as_skills(self) -> None:
        sources = {a.source for a in get_assets_by_category("skill")}
        assert sources == {f"skills/tdd-pair/{name}" for name in SKILL_FILES}

    def test_skill_assets_install_into_their_own_directory(self) -> None:
        for asset in get_assets_by_category("skill"):
            assert asset.target_subdir == "skills/tdd-pair"

    def test_every_registered_source_exists(self) -> None:
        for asset in CORE_ASSETS:
            assert (get_assets_dir() / asset.source).exists(), asset.source


class TestInstall:
    def test_install_places_skill_files_under_skills_dir(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        for name in SKILL_FILES:
            assert (install_dir / "skills" / "tdd-pair" / name).exists()

    def test_install_tracks_skill_files_in_manifest(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        manifest = load_manifest(install_dir / ".workflow-kit" / "manifest.json")
        assert manifest is not None
        sources = {e.source for e in manifest.files}
        assert {f"skills/tdd-pair/{name}" for name in SKILL_FILES} <= sources

    def test_install_does_not_reference_skills_in_claude_md(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)

        assert "tdd-pair" not in (install_dir / "CLAUDE.md").read_text()

    def test_dry_run_creates_no_skill_files(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir, dry_run=True)

        assert not (install_dir / "skills").exists()

    def test_force_install_restores_a_modified_skill(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        skill = install_dir / "skills" / "tdd-pair" / "SKILL.md"
        skill.write_text("tampered")

        install_command(claude_home=install_dir, force=True)

        assert skill.read_text() != "tampered"


class TestUninstall:
    def test_uninstall_removes_skill_files_and_empty_directory(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        uninstall_command(claude_home=install_dir)

        assert not (install_dir / "skills" / "tdd-pair").exists()

    def test_uninstall_keeps_directory_holding_user_files(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        notes = install_dir / "skills" / "tdd-pair" / "my-notes.md"
        notes.write_text("mine")

        uninstall_command(claude_home=install_dir)

        assert notes.read_text() == "mine"
        assert not (install_dir / "skills" / "tdd-pair" / "SKILL.md").exists()

    def test_uninstall_leaves_other_skills_alone(self, install_dir: Path) -> None:
        other = install_dir / "skills" / "other" / "SKILL.md"
        other.parent.mkdir(parents=True)
        other.write_text("not ours")
        install_command(claude_home=install_dir)

        uninstall_command(claude_home=install_dir)

        assert other.read_text() == "not ours"

    def test_uninstall_keep_files_keeps_skill(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        uninstall_command(claude_home=install_dir, keep_files=True)

        assert (install_dir / "skills" / "tdd-pair" / "SKILL.md").exists()


class TestUpdate:
    def test_update_restores_a_deleted_skill_file(self, install_dir: Path) -> None:
        install_command(claude_home=install_dir)
        target = install_dir / "skills" / "tdd-pair" / "outcome.schema.json"
        target.unlink()

        update_command(claude_home=install_dir)

        assert target.exists()


class TestListCLI:
    def test_list_skills(self) -> None:
        result = runner.invoke(app, ["list", "skills"])
        assert result.exit_code == 0
        assert "SKILL.md" in result.output
        assert "outcome.schema.json" in result.output


class TestPackagedSkillIsPortable:
    """The packaged skill must not depend on anything specific to the author's machine."""

    def test_has_no_absolute_user_paths(self, skill_md: str) -> None:
        assert "/Users/" not in skill_md
        assert "/home/" not in skill_md

    def test_does_not_reference_private_knowledge_files(self, skill_md: str) -> None:
        assert "knowledge/" not in skill_md

    def test_frontmatter_names_the_skill(self, skill_md: str) -> None:
        match = re.match(r"---\n(.*?)\n---\n", skill_md, re.DOTALL)
        assert match is not None
        assert re.search(r"^name: tdd-pair$", match.group(1), re.MULTILINE)

    def test_interactive_only_tools_are_not_pre_approved(self, skill_md: str) -> None:
        match = re.search(r"^allowed-tools:(.*)$", skill_md, re.MULTILINE)
        assert match is not None
        assert "AskUserQuestion" not in match.group(1)
        assert "PushNotification" not in match.group(1)

    def test_documents_a_headless_path_that_never_prompts(self, skill_md: str) -> None:
        assert "--headless" in skill_md
        assert "outcome.schema.json" in skill_md

    def test_commits_remain_a_human_action(self, skill_md: str) -> None:
        assert "Never commit" in skill_md

    def test_stays_under_the_file_size_limit(self, skill_md: str) -> None:
        assert len(skill_md.splitlines()) < 500
