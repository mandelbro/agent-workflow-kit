"""CLI application entry point for agent-workflow-kit."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from claude_workflow_kit.cli.install import install_command, uninstall_command
from claude_workflow_kit.cli.status import doctor_command, list_command, status_command
from claude_workflow_kit.cli.update import diff_command, update_command

app = typer.Typer(
    name="agent-kit",
    help="Manage Claude Code subagent personas and workflow knowledge assets.",
    no_args_is_help=True,
)
console = Console()

ClaudeHomePath = Annotated[
    Path | None,
    typer.Option(
        "--claude-home",
        help="Override the Claude Code home directory (default: ~/.claude).",
        envvar="CLAUDE_HOME",
    ),
]


@app.command()
def install(
    claude_home: ClaudeHomePath = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite without prompting.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would happen without making changes.")
    ] = False,
    skip_claude_md: Annotated[
        bool, typer.Option("--skip-claude-md", help="Skip CLAUDE.md section injection.")
    ] = False,
) -> None:
    """Install agent personas, workflows, and guidelines into ~/.claude/."""
    install_command(
        claude_home=claude_home,
        force=force,
        dry_run=dry_run,
        skip_claude_md=skip_claude_md,
    )


@app.command()
def uninstall(
    claude_home: ClaudeHomePath = None,
    keep_files: Annotated[
        bool,
        typer.Option("--keep-files", help="Only remove manifest and CLAUDE.md section."),
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would happen without making changes.")
    ] = False,
) -> None:
    """Remove managed files and CLAUDE.md section."""
    uninstall_command(claude_home=claude_home, keep_files=keep_files, dry_run=dry_run)


@app.command()
def update(
    claude_home: ClaudeHomePath = None,
    force: Annotated[bool, typer.Option("--force", help="Overwrite modified files.")] = False,
    check_only: Annotated[
        bool, typer.Option("--check-only", help="Report status without modifying.")
    ] = False,
) -> None:
    """Check for and apply updates to installed assets."""
    update_command(claude_home=claude_home, force=force, check_only=check_only)


@app.command()
def status(
    claude_home: ClaudeHomePath = None,
) -> None:
    """Show the status of all managed files."""
    status_command(claude_home=claude_home)


@app.command(name="list")
def list_assets(
    category: Annotated[
        str,
        typer.Argument(help="Category to list: agents, workflows, or guidelines."),
    ] = "all",
) -> None:
    """List available agents, workflows, or guidelines."""
    list_command(category=category)


@app.command()
def diff(
    file: Annotated[str, typer.Argument(help="Asset source path to diff (e.g. agents/Norwood.md)")],
    claude_home: ClaudeHomePath = None,
) -> None:
    """Show diff between installed and bundled version of a file."""
    diff_command(file=file, claude_home=claude_home)


@app.command()
def doctor(
    claude_home: ClaudeHomePath = None,
) -> None:
    """Validate the installation and check for issues."""
    doctor_command(claude_home=claude_home)
