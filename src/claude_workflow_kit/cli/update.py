"""Update and diff commands for agent-workflow-kit."""

from __future__ import annotations

import difflib
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from claude_workflow_kit.core.config import get_config
from claude_workflow_kit.core.file_ops import copy_file
from claude_workflow_kit.core.manifest import (
    FileStatus,
    check_file_status,
    file_checksum,
    load_manifest,
    save_manifest,
)
from claude_workflow_kit.core.registry import get_assets_dir

console = Console()


def update_command(
    *,
    claude_home: Path | None = None,
    force: bool = False,
    check_only: bool = False,
) -> None:
    """Check for and apply updates to installed assets."""
    config = get_config(claude_home)
    manifest = load_manifest(config.manifest_path)

    if manifest is None:
        console.print(
            "[yellow]Agent Workflow Kit is not installed.[/yellow] "
            "Run [bold]agent-kit install[/bold] first."
        )
        return

    assets_dir = get_assets_dir()
    updates_available = False

    table = Table(title="Update Check")
    table.add_column("Asset", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Action", style="dim")

    for entry in manifest.files:
        file_status = check_file_status(entry)
        target = Path(entry.target)

        # Find the corresponding source asset
        source_path = assets_dir / entry.source
        if not source_path.exists():
            table.add_row(entry.source, "[red]source missing[/red]", "skip")
            continue

        upstream_hash = file_checksum(source_path)
        upstream_changed = upstream_hash != entry.checksum

        if file_status == FileStatus.MISSING:
            table.add_row(entry.source, "[red]missing[/red]", "reinstall")
            updates_available = True
            if not check_only:
                copy_file(source_path, target, create_backup=False)
                entry.checksum = file_checksum(target)

        elif file_status == FileStatus.CURRENT and upstream_changed:
            table.add_row(entry.source, "[yellow]outdated[/yellow]", "update")
            updates_available = True
            if not check_only:
                copy_file(source_path, target, create_backup=True)
                entry.checksum = file_checksum(target)

        elif file_status == FileStatus.USER_MODIFIED and upstream_changed:
            if force:
                table.add_row(entry.source, "[yellow]conflict[/yellow]", "force overwrite")
                if not check_only:
                    copy_file(source_path, target, create_backup=True)
                    entry.checksum = file_checksum(target)
            else:
                table.add_row(
                    entry.source,
                    "[yellow]conflict[/yellow]",
                    "skipped (use --force)",
                )
            updates_available = True

        elif file_status == FileStatus.USER_MODIFIED:
            table.add_row(entry.source, "[blue]user modified[/blue]", "no upstream change")

        else:
            table.add_row(entry.source, "[green]current[/green]", "none")

    console.print(table)

    if check_only:
        if updates_available:
            console.print("\n[yellow]Updates available. Run agent-kit update to apply.[/yellow]")
        else:
            console.print("\n[green]Everything is up to date.[/green]")
        return

    if updates_available:
        save_manifest(manifest, config.manifest_path)
        console.print("\n[bold green]Update complete![/bold green]")
    else:
        console.print("\n[green]Everything is up to date.[/green]")


def diff_command(
    *,
    file: str,
    claude_home: Path | None = None,
) -> None:
    """Show diff between installed and bundled version of a file."""
    config = get_config(claude_home)
    manifest = load_manifest(config.manifest_path)

    if manifest is None:
        console.print("[yellow]Agent Workflow Kit is not installed.[/yellow]")
        return

    # Find the entry
    entry = next((e for e in manifest.files if e.source == file), None)
    if entry is None:
        console.print(f"[red]File '{file}' is not managed by Agent Workflow Kit.[/red]")
        console.print("[dim]Managed files:[/dim]")
        for e in manifest.files:
            console.print(f"  {e.source}")
        return

    target = Path(entry.target)
    source = get_assets_dir() / entry.source

    if not target.exists():
        console.print(f"[red]Installed file not found: {target}[/red]")
        return

    if not source.exists():
        console.print(f"[red]Bundled source not found: {source}[/red]")
        return

    installed_lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    bundled_lines = source.read_text(encoding="utf-8").splitlines(keepends=True)

    diff_lines = difflib.unified_diff(
        installed_lines,
        bundled_lines,
        fromfile=f"installed: {entry.target}",
        tofile=f"bundled: {entry.source}",
    )
    diff_text = "".join(diff_lines)

    if not diff_text:
        console.print(f"[green]No differences for {file}.[/green]")
        return

    console.print(
        Panel(
            Syntax(diff_text, "diff", theme="monokai"),
            title=f"Diff: {file}",
            border_style="blue",
        )
    )
