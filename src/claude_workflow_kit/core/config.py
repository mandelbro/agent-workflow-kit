"""Configuration module for agent-workflow-kit."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class AgentKitConfig(BaseSettings):
    """Configuration for agent-workflow-kit paths and settings."""

    claude_home: Path = Field(
        default_factory=lambda: Path(os.environ.get("CLAUDE_HOME", "~/.claude")).expanduser(),
        description="Root directory for Claude Code configuration.",
    )

    @property
    def agents_dir(self) -> Path:
        """Directory containing agent persona definitions."""
        return self.claude_home / "agents"

    @property
    def knowledge_dir(self) -> Path:
        """Directory containing knowledge assets."""
        return self.claude_home / "knowledge"

    @property
    def workflows_dir(self) -> Path:
        """Directory containing workflow definitions."""
        return self.knowledge_dir / "workflows"

    @property
    def guidelines_dir(self) -> Path:
        """Directory containing guideline documents."""
        return self.knowledge_dir

    @property
    def coding_principles_dir(self) -> Path:
        """Directory containing coding principle documents."""
        return self.knowledge_dir / "coding-principles"

    @property
    def manifest_dir(self) -> Path:
        """Directory for workflow-kit internal state."""
        return self.claude_home / ".workflow-kit"

    @property
    def manifest_path(self) -> Path:
        """Path to the installed-assets manifest file."""
        return self.manifest_dir / "manifest.json"

    @property
    def claude_md_path(self) -> Path:
        """Path to the user's CLAUDE.md file."""
        return self.claude_home / "CLAUDE.md"

    def ensure_dirs(self) -> None:
        """Create all required directories if they don't exist."""
        for d in [
            self.agents_dir,
            self.workflows_dir,
            self.guidelines_dir,
            self.coding_principles_dir,
            self.manifest_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)


def get_config(claude_home: Path | None = None) -> AgentKitConfig:
    """Create a config, optionally overriding CLAUDE_HOME."""
    if claude_home is not None:
        return AgentKitConfig(claude_home=claude_home)
    return AgentKitConfig()
