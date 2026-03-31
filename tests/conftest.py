"""Shared test fixtures for agent-workflow-kit."""

from pathlib import Path

import pytest


@pytest.fixture
def claude_home(tmp_path: Path) -> Path:
    """Provide an isolated CLAUDE_HOME directory for testing."""
    home = tmp_path / ".claude"
    home.mkdir()
    return home


@pytest.fixture
def assets_dir() -> Path:
    """Return the path to bundled assets in the source tree."""
    return Path(__file__).resolve().parent.parent / "src" / "claude_workflow_kit" / "assets"
