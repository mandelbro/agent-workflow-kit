"""Tests for claude_workflow_kit.core.config."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from claude_workflow_kit.core.config import AgentKitConfig, get_config

if TYPE_CHECKING:
    import pytest


class TestAgentKitConfigDefaults:
    """Default configuration values."""

    def test_default_claude_home_points_to_user_dot_claude(self) -> None:
        cfg = AgentKitConfig()
        assert cfg.claude_home == Path.home() / ".claude"

    def test_claude_home_is_expanded(self) -> None:
        cfg = AgentKitConfig()
        assert "~" not in str(cfg.claude_home)


class TestAgentKitConfigOverride:
    """Configuration with an explicit claude_home override."""

    def test_claude_home_can_be_overridden_via_constructor(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.claude_home == claude_home

    def test_override_via_env_var(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        custom = tmp_path / "custom-claude"
        monkeypatch.setenv("CLAUDE_HOME", str(custom))
        cfg = AgentKitConfig()
        assert cfg.claude_home == custom


class TestDerivedPaths:
    """All derived paths are correct relative to claude_home."""

    def test_agents_dir(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.agents_dir == claude_home / "agents"

    def test_knowledge_dir(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.knowledge_dir == claude_home / "knowledge"

    def test_workflows_dir(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.workflows_dir == claude_home / "knowledge" / "workflows"

    def test_guidelines_dir_is_knowledge_dir(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.guidelines_dir == cfg.knowledge_dir

    def test_coding_principles_dir(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.coding_principles_dir == claude_home / "knowledge" / "coding-principles"

    def test_manifest_dir(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.manifest_dir == claude_home / ".workflow-kit"

    def test_manifest_path(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.manifest_path == claude_home / ".workflow-kit" / "manifest.json"

    def test_claude_md_path(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        assert cfg.claude_md_path == claude_home / "CLAUDE.md"


class TestEnsureDirs:
    """ensure_dirs creates all expected directories."""

    def test_creates_all_required_directories(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        cfg.ensure_dirs()

        assert cfg.agents_dir.is_dir()
        assert cfg.workflows_dir.is_dir()
        assert cfg.guidelines_dir.is_dir()
        assert cfg.coding_principles_dir.is_dir()
        assert cfg.manifest_dir.is_dir()

    def test_is_idempotent(self, claude_home: Path) -> None:
        cfg = AgentKitConfig(claude_home=claude_home)
        cfg.ensure_dirs()
        cfg.ensure_dirs()  # calling twice should not raise

        assert cfg.agents_dir.is_dir()


class TestGetConfigFactory:
    """get_config() factory function."""

    def test_returns_default_config_without_override(self) -> None:
        cfg = get_config()
        assert cfg.claude_home == Path.home() / ".claude"

    def test_returns_overridden_config_with_path(self, claude_home: Path) -> None:
        cfg = get_config(claude_home=claude_home)
        assert cfg.claude_home == claude_home

    def test_factory_returns_agent_kit_config_instance(self) -> None:
        cfg = get_config()
        assert isinstance(cfg, AgentKitConfig)
