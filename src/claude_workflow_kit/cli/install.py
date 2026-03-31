"""Install and uninstall commands for agent-workflow-kit."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from claude_workflow_kit.core.claude_md import (
    build_managed_section,
    inject_section,
    read_claude_md,
    remove_section,
)
from claude_workflow_kit.core.config import AgentKitConfig, get_config
from claude_workflow_kit.core.file_ops import atomic_write, copy_file, remove_file
from claude_workflow_kit.core.manifest import (
    FileEntry,
    Manifest,
    file_checksum,
    load_manifest,
    save_manifest,
)
from claude_workflow_kit.core.registry import CORE_ASSETS, get_assets_dir

console = Console()


def install_command(
    *,
    claude_home: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
    skip_claude_md: bool = False,
) -> None:
    """Execute the install flow."""
    config = get_config(claude_home)
    assets_dir = get_assets_dir()
    existing_manifest = load_manifest(config.manifest_path)

    if existing_manifest and not force:
        console.print(
            "[yellow]Agent Workflow Kit is already installed.[/yellow] "
            "Use [bold]--force[/bold] to reinstall or [bold]agent-kit update[/bold] to update."
        )
        return

    if not dry_run:
        config.ensure_dirs()

    table = Table(title="Installing Agent Workflow Kit")
    table.add_column("Asset", style="cyan")
    table.add_column("Target", style="green")
    table.add_column("Status", style="bold")

    entries: list[FileEntry] = []

    for asset in CORE_ASSETS:
        source_path = assets_dir / asset.source
        target_path = config.claude_home / asset.target_subdir / source_path.name

        if not source_path.exists():
            table.add_row(asset.source, str(target_path), "[red]missing source[/red]")
            continue

        status_msg = "[green]installed[/green]"
        if target_path.exists() and not force:
            status_msg = "[yellow]skipped (exists)[/yellow]"
        elif target_path.exists() and force:
            status_msg = "[green]overwritten[/green]"

        table.add_row(asset.source, str(target_path), status_msg)

        if not dry_run:
            if not target_path.exists() or force:
                copy_file(source_path, target_path, create_backup=target_path.exists())

            checksum = file_checksum(target_path)
            entries.append(
                FileEntry(
                    source=asset.source,
                    target=str(target_path),
                    checksum=checksum,
                    installed_at=datetime.now(UTC).isoformat(),
                )
            )

    console.print(table)

    # CLAUDE.md injection
    if not skip_claude_md:
        _inject_claude_md(config, dry_run)

    # Save manifest
    if not dry_run and entries:
        manifest = Manifest(files=entries)
        save_manifest(manifest, config.manifest_path)
        console.print(f"\n[dim]Manifest saved to {config.manifest_path}[/dim]")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes were made.[/yellow]")
    else:
        console.print("\n[bold green]Installation complete![/bold green]")


def _inject_claude_md(config: AgentKitConfig, dry_run: bool) -> None:
    """Inject the managed section into CLAUDE.md."""
    agents = [
        (a.description, str(config.claude_home / a.target_subdir / a.source.split("/")[-1]))
        for a in CORE_ASSETS
        if a.category == "agent"
    ]
    workflows = [
        (a.description, str(config.claude_home / a.target_subdir / a.source.split("/")[-1]))
        for a in CORE_ASSETS
        if a.category == "workflow"
    ]
    guidelines = [
        (a.description, str(config.claude_home / a.target_subdir / a.source.split("/")[-1]))
        for a in CORE_ASSETS
        if a.category == "guideline"
    ]

    section = build_managed_section(agents, workflows, guidelines)
    current_content = read_claude_md(config.claude_md_path)
    new_content = inject_section(current_content, section)

    if dry_run:
        console.print("\n[dim]Would inject managed section into CLAUDE.md[/dim]")
    else:
        atomic_write(config.claude_md_path, new_content)
        console.print(f"\n[dim]CLAUDE.md updated at {config.claude_md_path}[/dim]")


def uninstall_command(
    *,
    claude_home: Path | None = None,
    keep_files: bool = False,
    dry_run: bool = False,
) -> None:
    """Execute the uninstall flow."""
    config = get_config(claude_home)
    manifest = load_manifest(config.manifest_path)

    if manifest is None:
        console.print("[yellow]Agent Workflow Kit is not installed.[/yellow]")
        return

    table = Table(title="Uninstalling Agent Workflow Kit")
    table.add_column("File", style="cyan")
    table.add_column("Status", style="bold")

    if not keep_files:
        for entry in manifest.files:
            target = Path(entry.target)
            if dry_run:
                status_msg = (
                    "[yellow]would remove[/yellow]" if target.exists() else "[dim]missing[/dim]"
                )
            else:
                removed = remove_file(target)
                status_msg = "[green]removed[/green]" if removed else "[dim]missing[/dim]"
            table.add_row(entry.source, status_msg)
    else:
        console.print("[dim]Keeping installed files (--keep-files).[/dim]")

    console.print(table)

    # Remove CLAUDE.md section
    current_content = read_claude_md(config.claude_md_path)
    if current_content:
        new_content = remove_section(current_content)
        if new_content != current_content:
            if dry_run:
                console.print("[dim]Would remove managed section from CLAUDE.md[/dim]")
            else:
                atomic_write(config.claude_md_path, new_content)
                console.print("[dim]Removed managed section from CLAUDE.md[/dim]")

    # Remove manifest
    if not dry_run:
        remove_file(config.manifest_path)
        console.print(f"[dim]Manifest removed from {config.manifest_path}[/dim]")

    if dry_run:
        console.print("\n[yellow]Dry run — no changes were made.[/yellow]")
    else:
        console.print("\n[bold green]Uninstall complete![/bold green]")
