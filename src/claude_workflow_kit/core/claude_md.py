"""CLAUDE.md sentinel-based section management."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

SENTINEL_BEGIN = "<!-- agent-kit:begin -- managed by agent-workflow-kit, do not edit -->"
SENTINEL_END = "<!-- agent-kit:end -->"


def inject_section(content: str, section: str) -> str:
    """Replace or append the managed section in CLAUDE.md content.

    Args:
        content: Current CLAUDE.md content (may be empty).
        section: The content to place between sentinels.

    Returns:
        Updated CLAUDE.md content with managed section injected.
    """
    managed_block = f"{SENTINEL_BEGIN}\n{section}\n{SENTINEL_END}"

    begin_idx = content.find(SENTINEL_BEGIN)
    end_idx = content.find(SENTINEL_END)

    if begin_idx != -1 and end_idx != -1:
        after_end = end_idx + len(SENTINEL_END)
        return content[:begin_idx] + managed_block + content[after_end:]

    # Append to end with proper spacing
    if content and not content.endswith("\n\n"):
        separator = "\n\n" if content.endswith("\n") else "\n\n"
    elif not content:
        separator = ""
    else:
        separator = ""
    return content + separator + managed_block + "\n"


def remove_section(content: str) -> str:
    """Remove the managed section from CLAUDE.md content.

    Returns:
        Content with managed section removed. Preserves surrounding content.
    """
    begin_idx = content.find(SENTINEL_BEGIN)
    end_idx = content.find(SENTINEL_END)

    if begin_idx == -1 or end_idx == -1:
        return content

    after_end = end_idx + len(SENTINEL_END)
    # Consume trailing newline if present
    if after_end < len(content) and content[after_end] == "\n":
        after_end += 1

    before = content[:begin_idx]
    after = content[after_end:]

    # Clean up extra blank lines at the junction
    result = before.rstrip("\n")
    if after.strip():
        result += "\n\n" + after.lstrip("\n")
    elif result:
        result += "\n"
    return result


def has_managed_section(content: str) -> bool:
    """Check if CLAUDE.md content contains the managed section."""
    return SENTINEL_BEGIN in content and SENTINEL_END in content


def read_claude_md(path: Path) -> str:
    """Read CLAUDE.md, returning empty string if it doesn't exist."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_managed_section(
    agents: list[tuple[str, str]],
    workflows: list[tuple[str, str]],
    guidelines: list[tuple[str, str]],
) -> str:
    """Build the managed section content from installed assets.

    Each tuple is (description, file_path) where file_path is the
    absolute path to the installed file.

    Args:
        agents: List of (description, path) for agent personas.
        workflows: List of (description, path) for workflows.
        guidelines: List of (description, path) for guidelines.

    Returns:
        The section content (without sentinels).
    """
    lines: list[str] = []

    if agents:
        lines.append("## Agent Kit Agents\n")
        for desc, path in agents:
            lines.append(f"- {desc}: @{path}")
        lines.append("")

    if workflows:
        lines.append("## Agent Kit Workflows\n")
        for desc, path in workflows:
            lines.append(f"- {desc}: @{path}")
        lines.append("")

    if guidelines:
        lines.append("## Agent Kit Guidelines\n")
        for desc, path in guidelines:
            lines.append(f"- {desc}: @{path}")
        lines.append("")

    return "\n".join(lines).rstrip("\n")
