"""Every agent asset must carry frontmatter so Claude Code registers it as a subagent."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from claude_workflow_kit.core.registry import get_assets_by_category, get_assets_dir

if TYPE_CHECKING:
    from pathlib import Path

AGENT_FILES = [get_assets_dir() / a.source for a in get_assets_by_category("agent")]


def _frontmatter(path: Path) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.DOTALL)
    assert match is not None, f"{path.name} has no frontmatter block"
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip().strip('"')
    return fields


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
class TestAgentFrontmatter:
    def test_has_name_matching_the_file(self, path: Path) -> None:
        assert _frontmatter(path).get("name") == path.stem

    def test_has_a_description(self, path: Path) -> None:
        assert len(_frontmatter(path).get("description", "")) >= 20
