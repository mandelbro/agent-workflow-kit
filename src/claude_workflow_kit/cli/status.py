"""Status, list, and doctor commands for agent-workflow-kit."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from claude_workflow_kit.core.claude_md import has_managed_section, read_claude_md
from claude_workflow_kit.core.config import get_config
from claude_workflow_kit.core.manifest import (
    FileStatus,
    check_file_status,
    load_manifest,
)
from claude_workflow_kit.core.registry import CORE_ASSETS

console = Console()

_STATUS_STYLE = {
    FileStatus.CURRENT: ("[green]current[/green]", "green"),
    FileStatus.USER_MODIFIED: ("[blue]modified[/blue]", "blue"),
    FileStatus.MISSING: ("[red]missing[/red]", "red"),
    FileStatus.OUTDATED: ("[yellow]outdated[/yellow]", "yellow"),
}


def status_command(*, claude_home: Path | None = None) -> None:
    """Show the status of all managed files."""
    config = get_config(claude_home)
    manifest = load_manifest(config.manifest_path)

    if manifest is None:
        console.print("[yellow]Agent Workflow Kit is not installed.[/yellow]")
        return

    table = Table(title="Agent Workflow Kit Status")
    table.add_column("Asset", style="cyan")
    table.add_column("Target", style="dim")
    table.add_column("Status", style="bold")

    for entry in manifest.files:
        file_status = check_file_status(entry)
        styled, _ = _STATUS_STYLE.get(file_status, (str(file_status), "white"))
        table.add_row(entry.source, entry.target, styled)

    console.print(table)
    console.print(f"\n[dim]Version: {manifest.version} | Installed: {manifest.installed_at}[/dim]")


def list_command(*, category: str = "all") -> None:
    """List available agents, workflows, or guidelines."""
    category_map = {
        "agents": "agent",
        "agent": "agent",
        "workflows": "workflow",
        "workflow": "workflow",
        "guidelines": "guideline",
        "guideline": "guideline",
    }

    if category != "all" and category not in category_map:
        console.print(
            f"[red]Unknown category: {category}[/red]\n"
            "Valid categories: agents, workflows, guidelines"
        )
        return

    table = Table(title="Available Assets")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="blue")
    table.add_column("Description")

    for asset in CORE_ASSETS:
        if category == "all" or asset.category == category_map.get(category, category):
            name = asset.source.split("/")[-1]
            table.add_row(name, asset.category, asset.description)

    console.print(table)


def doctor_command(*, claude_home: Path | None = None) -> None:
    """Validate the installation and check for issues."""
    config = get_config(claude_home)
    issues: list[str] = []
    checks_passed = 0
    total_checks = 0

    def check(name: str, ok: bool, fix_hint: str = "") -> None:
        nonlocal checks_passed, total_checks
        total_checks += 1
        if ok:
            checks_passed += 1
            console.print(f"  [green]OK[/green]  {name}")
        else:
            msg = f"  [red]FAIL[/red]  {name}"
            if fix_hint:
                msg += f" — {fix_hint}"
            console.print(msg)
            issues.append(name)

    console.print(Panel("[bold]Agent Workflow Kit Doctor[/bold]", border_style="blue"))

    # Check CLAUDE_HOME exists
    check(
        f"CLAUDE_HOME exists ({config.claude_home})",
        config.claude_home.exists(),
        "Directory does not exist. Run: agent-kit install",
    )

    # Check CLAUDE_HOME is writable
    check(
        "CLAUDE_HOME is writable",
        config.claude_home.exists() and config.claude_home.is_dir(),
        "Cannot write to CLAUDE_HOME directory",
    )

    # Check manifest exists
    manifest = load_manifest(config.manifest_path)
    check(
        "Manifest exists",
        manifest is not None,
        "Not installed. Run: agent-kit install",
    )

    if manifest is not None:
        # Check each managed file
        missing_count = 0
        for entry in manifest.files:
            target = Path(entry.target)
            if not target.exists():
                missing_count += 1

        check(
            f"All managed files present ({len(manifest.files) - missing_count}/{len(manifest.files)})",
            missing_count == 0,
            f"{missing_count} file(s) missing. Run: agent-kit update",
        )

        # Check CLAUDE.md section
        claude_content = read_claude_md(config.claude_md_path)
        check(
            "CLAUDE.md managed section present",
            has_managed_section(claude_content),
            "Run: agent-kit install --force",
        )

    # Check required directories
    for dir_name, dir_path in [
        ("agents/", config.agents_dir),
        ("knowledge/workflows/", config.workflows_dir),
        ("knowledge/coding-principles/", config.coding_principles_dir),
    ]:
        check(f"Directory exists: {dir_name}", dir_path.exists())

    console.print()
    if issues:
        console.print(
            f"[bold yellow]{checks_passed}/{total_checks} checks passed. "
            f"{len(issues)} issue(s) found.[/bold yellow]"
        )
    else:
        console.print(
            f"[bold green]All {total_checks} checks passed. Installation is healthy![/bold green]"
        )
