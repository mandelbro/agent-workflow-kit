"""Tests for claude_workflow_kit.core.claude_md."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from claude_workflow_kit.core.claude_md import (
    SENTINEL_BEGIN,
    SENTINEL_END,
    build_managed_section,
    has_managed_section,
    inject_section,
    read_claude_md,
    remove_section,
)


class TestInjectSection:
    """inject_section appends or replaces the managed block."""

    def test_appends_to_empty_content(self) -> None:
        result = inject_section("", "managed content")
        assert result.startswith(SENTINEL_BEGIN)
        assert "managed content" in result
        assert result.endswith(SENTINEL_END + "\n")

    def test_appends_to_existing_content_with_proper_spacing(self) -> None:
        existing = "# My Config\n\nSome user content.\n"
        result = inject_section(existing, "managed content")

        # User content is preserved at the top
        assert result.startswith("# My Config\n\nSome user content.\n")
        # Blank line separates user content from managed block
        assert "\n\n" + SENTINEL_BEGIN in result
        assert result.endswith(SENTINEL_END + "\n")

    def test_replaces_existing_managed_section(self) -> None:
        original = inject_section("", "old content")
        result = inject_section(original, "new content")

        assert "old content" not in result
        assert "new content" in result
        # Only one pair of sentinels
        assert result.count(SENTINEL_BEGIN) == 1
        assert result.count(SENTINEL_END) == 1

    def test_preserves_user_content_before_managed_section(self) -> None:
        before = "# User Header\n\nImportant notes.\n"
        with_section = inject_section(before, "v1")
        updated = inject_section(with_section, "v2")

        assert updated.startswith("# User Header\n\nImportant notes.\n")
        assert "v2" in updated
        assert "v1" not in updated

    def test_preserves_user_content_after_managed_section(self) -> None:
        # Manually construct content with user text after the managed block
        managed_block = f"{SENTINEL_BEGIN}\nold stuff\n{SENTINEL_END}"
        content = f"# Before\n\n{managed_block}\n\n# After\n"

        result = inject_section(content, "new stuff")

        assert "# Before" in result
        assert "# After" in result
        assert "new stuff" in result
        assert "old stuff" not in result


class TestRemoveSection:
    """remove_section strips the managed block cleanly."""

    def test_removes_managed_section(self) -> None:
        content = inject_section("", "managed content")
        result = remove_section(content)

        assert SENTINEL_BEGIN not in result
        assert SENTINEL_END not in result
        assert "managed content" not in result

    def test_returns_unchanged_when_no_section_exists(self) -> None:
        original = "# Just user content\n"
        assert remove_section(original) == original

    def test_preserves_user_content_outside_section(self) -> None:
        managed_block = f"{SENTINEL_BEGIN}\nmanaged\n{SENTINEL_END}"
        content = f"# Before\n\n{managed_block}\n\n# After\n"

        result = remove_section(content)

        assert "# Before" in result
        assert "# After" in result
        assert "managed" not in result


class TestHasManagedSection:
    """has_managed_section detects sentinel presence."""

    def test_returns_true_when_sentinels_present(self) -> None:
        content = f"stuff\n{SENTINEL_BEGIN}\nhello\n{SENTINEL_END}\nmore"
        assert has_managed_section(content) is True

    def test_returns_false_when_no_sentinels(self) -> None:
        assert has_managed_section("# Plain CLAUDE.md\n") is False

    def test_returns_false_with_only_begin_sentinel(self) -> None:
        assert has_managed_section(f"text\n{SENTINEL_BEGIN}\n") is False

    def test_returns_false_with_only_end_sentinel(self) -> None:
        assert has_managed_section(f"text\n{SENTINEL_END}\n") is False


class TestReadClaudeMd:
    """read_claude_md handles missing and existing files."""

    def test_returns_empty_string_for_missing_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "CLAUDE.md"
        assert read_claude_md(missing) == ""

    def test_returns_file_content_when_file_exists(self, tmp_path: Path) -> None:
        md_file = tmp_path / "CLAUDE.md"
        md_file.write_text("# Hello\n", encoding="utf-8")
        assert read_claude_md(md_file) == "# Hello\n"


class TestBuildManagedSection:
    """build_managed_section produces correct markdown from asset lists."""

    def test_builds_all_three_categories(self) -> None:
        agents = [("Coder persona", "/home/.claude/agents/coder.md")]
        workflows = [("TDD workflow", "/home/.claude/knowledge/workflows/tdd.md")]
        guidelines = [("Style guide", "/home/.claude/knowledge/style.md")]

        result = build_managed_section(agents, workflows, guidelines)

        assert "## Agent Kit Agents" in result
        assert "- Coder persona: @/home/.claude/agents/coder.md" in result
        assert "## Agent Kit Workflows" in result
        assert "- TDD workflow: @/home/.claude/knowledge/workflows/tdd.md" in result
        assert "## Agent Kit Guidelines" in result
        assert "- Style guide: @/home/.claude/knowledge/style.md" in result

    def test_handles_empty_lists_gracefully(self) -> None:
        result = build_managed_section([], [], [])
        assert result == ""

    def test_handles_only_agents(self) -> None:
        result = build_managed_section(
            agents=[("Ada", "/agents/ada.md")],
            workflows=[],
            guidelines=[],
        )
        assert "## Agent Kit Agents" in result
        assert "- Ada: @/agents/ada.md" in result
        assert "## Agent Kit Workflows" not in result
        assert "## Agent Kit Guidelines" not in result

    def test_handles_only_workflows(self) -> None:
        result = build_managed_section(
            agents=[],
            workflows=[("Deploy", "/workflows/deploy.md")],
            guidelines=[],
        )
        assert "## Agent Kit Workflows" in result
        assert "## Agent Kit Agents" not in result

    def test_handles_only_guidelines(self) -> None:
        result = build_managed_section(
            agents=[],
            workflows=[],
            guidelines=[("Naming", "/knowledge/naming.md")],
        )
        assert "## Agent Kit Guidelines" in result
        assert "## Agent Kit Agents" not in result

    def test_multiple_items_per_category(self) -> None:
        agents = [
            ("Coder", "/agents/coder.md"),
            ("Reviewer", "/agents/reviewer.md"),
        ]
        result = build_managed_section(agents, [], [])

        assert "- Coder: @/agents/coder.md" in result
        assert "- Reviewer: @/agents/reviewer.md" in result
