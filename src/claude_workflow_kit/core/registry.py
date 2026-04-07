"""Asset registry — maps bundled files to their install targets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AssetEntry:
    """A single bundled asset with its source path, target subdirectory, and description."""

    source: str  # relative path within assets/ dir (e.g. "agents/Norwood.md")
    target_subdir: str  # subdirectory under CLAUDE_HOME (e.g. "agents")
    description: str  # human-readable description for CLAUDE.md references
    category: str  # "agent", "workflow", or "guideline"


CORE_ASSETS: list[AssetEntry] = [
    # Agents
    AssetEntry("agents/Norwood.md", "agents", "Discovery and planning agent", "agent"),
    AssetEntry("agents/Eco.md", "agents", "Research agent", "agent"),
    AssetEntry("agents/Ive.md", "agents", "UX design agent", "agent"),
    AssetEntry("agents/Zod.md", "agents", "Technical review agent", "agent"),
    AssetEntry("agents/Shelly.md", "agents", "Task generation and sprint planning", "agent"),
    AssetEntry("agents/Ada.md", "agents", "Pair programming agent", "agent"),
    AssetEntry("agents/Sentinel.md", "agents", "Security review and threat modeling agent", "agent"),
    # Workflows
    AssetEntry(
        "workflows/tasks-workflow.md",
        "knowledge/workflows",
        "Task workflow system",
        "workflow",
    ),
    AssetEntry("workflows/retro.md", "knowledge/workflows", "Retrospective workflow", "workflow"),
    AssetEntry(
        "workflows/project-initialization.md",
        "knowledge/workflows",
        "Project initialization workflow",
        "workflow",
    ),
    # Guidelines
    AssetEntry(
        "guidelines/file-and-context-optimization.md",
        "knowledge",
        "File and context optimization guidelines",
        "guideline",
    ),
    AssetEntry(
        "guidelines/tool-utilization.md",
        "knowledge",
        "Tool utilization guidelines",
        "guideline",
    ),
    AssetEntry(
        "coding-principles/testing-strategy.md",
        "knowledge/coding-principles",
        "Testing-driven development strategy",
        "guideline",
    ),
]


def get_assets_dir() -> Path:
    """Return the path to the bundled assets directory."""
    return Path(__file__).resolve().parent.parent / "assets"


def get_assets_by_category(category: str) -> list[AssetEntry]:
    """Filter assets by category."""
    return [a for a in CORE_ASSETS if a.category == category]
