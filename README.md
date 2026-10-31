# agent-workflow-kit

[![PyPI version](https://img.shields.io/pypi/v/agent-workflow-kit.svg)](https://pypi.org/project/agent-workflow-kit/)
[![Python 3.12+](https://img.shields.io/pypi/pyversions/agent-workflow-kit.svg)](https://pypi.org/project/agent-workflow-kit/)
[![CI](https://github.com/mandelbro/agent-workflow-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/mandelbro/agent-workflow-kit/actions/workflows/ci.yml)

A Python CLI that packages, installs, and manages Claude Code subagent personas and workflow knowledge assets. It is the opinionated workflow layer that sits on top of [awesome-claude-hooks](https://github.com/mandelbro/awesome-claude-hooks) -- the two projects complement each other but remain independent.

## Why

Setting up a Claude Code workflow system on a new machine means manually copying 12+ markdown files into the right directories, editing `~/.claude/CLAUDE.md` to add `@` references, and hoping you remember which version is current. `agent-workflow-kit` automates that entire lifecycle: **install, update, customize, and uninstall** -- with checksums, backups, and conflict detection.

## Installation

```bash
pipx install agent-workflow-kit
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install agent-workflow-kit
```

Requires Python 3.12+.

## Quick Start

```bash
# Install all assets into ~/.claude/
agent-kit install

# Check installation health
agent-kit doctor

# See what's available
agent-kit list
```

## Commands

| Command | Description |
|---------|-------------|
| `agent-kit install` | Copy agents, workflows, guidelines, and skills to `~/.claude/`, inject managed section into `CLAUDE.md`, save manifest |
| `agent-kit uninstall` | Remove managed files, `CLAUDE.md` section, and manifest |
| `agent-kit update` | Detect upstream changes, handle conflicts with user-modified files |
| `agent-kit status` | Show the current state of all managed files |
| `agent-kit list [category]` | List available assets (`agents`, `workflows`, `guidelines`, `skills`, or `all`) |
| `agent-kit diff <file>` | Show diff between installed and bundled version of a file |
| `agent-kit doctor` | Validate installation health (directories, manifest, CLAUDE.md) |

### Common Flags

```bash
agent-kit install --dry-run          # Preview without making changes
agent-kit install --force            # Overwrite existing files (creates backups)
agent-kit install --skip-claude-md   # Install files without touching CLAUDE.md
agent-kit install --claude-home /path/to/dir  # Override default ~/.claude/
agent-kit update --check-only        # Report status without modifying
agent-kit update --force             # Overwrite user-modified files
agent-kit uninstall --keep-files     # Only remove manifest and CLAUDE.md section
```

## Bundled Assets

### Agents (installed to `~/.claude/agents/`)

| Agent | Description |
|-------|-------------|
| **Ada** | Pair programming agent -- TDD, architecture, mentoring |
| **Norwood** | Discovery and planning -- code archaeology, solution design, risk analysis |
| **Eco** | Research agent -- web search, documentation review, synthesis |
| **Ive** | UX design -- accessibility, interaction patterns, component specs |
| **Shelly** | Task generation and sprint planning -- story points, task breakdown |
| **Zod** | Technical review -- security, performance, maintainability audits |
| **Sentinel** | Security review -- STRIDE threat modeling, attack surface analysis, risk assessment |

### Skills (installed to `~/.claude/skills/<name>/`)

| Skill | Description |
|-------|-------------|
| **tdd-pair** | `/tdd-pair` -- drives Ada's red/green/refactor loop in test batches against a spec. `start` is human-gated, `auto` is gated by a Zod review, and `auto --headless` runs unattended (for `claude -p`) and ends with a JSON outcome |

Skills are slash-invoked, so they get no `CLAUDE.md` reference. `tdd-pair` expects the **Ada** and **Zod** agents from this kit, falls back to a general-purpose reviewer if Zod is not registered, and never commits.

#### tdd-pair headless outcome

`/tdd-pair auto --headless <spec>` never prompts. Its last message ends with one fenced `json` block that conforms to `skills/tdd-pair/outcome.schema.json` (also generated from `claude_workflow_kit.core.tdd_outcome.TddOutcome`):

| Field | Meaning |
|-------|---------|
| `schema_version` | Always `1` |
| `status` | `done`, `blocked` (needs a human; `blocked_reason` required), or `needs_info` (spec is not a usable contract; `spec_gaps` required) |
| `spec_path`, `base_branch`, `base_warning` | Which spec ran, against which base, and any staleness warning |
| `batches` | `id`, `name`, `status`, `phase`, `review_rounds`, `tests` per batch |
| `failing_checks` | Test/lint/typecheck commands failing at stop (must be empty for `done`) |
| `open_findings` | Unresolved reviewer findings: `batch_id`, `phase`, `severity`, `summary` |

The outcome is **advisory**: it comes from a model. Consumers should call `parse_outcome()` (fails closed on a missing, malformed, or schema-violating block), re-run the checks themselves, and never treat `done` as proof. Rate limits and crashes are detected by the caller from the process, not reported here.

### Workflows (installed to `~/.claude/knowledge/workflows/`)

| Workflow | Description |
|----------|-------------|
| **tasks-workflow** | Task Workflow System -- structured task tracking in `tasks/` directories |
| **retro** | Sprint retrospective process |
| **project-initialization** | New project setup with discovery, scaffolding, and task generation |

### Guidelines (installed to `~/.claude/knowledge/`)

| Guideline | Description |
|-----------|-------------|
| **file-and-context-optimization** | File size targets (100-500 lines), splitting strategies |
| **tool-utilization** | ReAct framework for tool calls |
| **testing-strategy** | TDD rules, testing pyramid, Red-Green-Refactor |

## How It Works

### Install Flow

1. Creates target directories under `~/.claude/` (agents, knowledge/workflows, etc.)
2. Copies each bundled asset (markdown, plus the tdd-pair JSON schema) to its target location
3. Injects a sentinel-bounded managed section into `~/.claude/CLAUDE.md` with `@` references
4. Writes a manifest (`~/.claude/.workflow-kit/manifest.json`) tracking installed files with SHA-256 checksums

### Update Flow

1. Reads the manifest to identify installed files
2. Compares on-disk checksums against manifest (detects user modifications)
3. Compares bundled assets against manifest (detects upstream changes)
4. For each file, reports one of: `current`, `user modified`, `outdated`, `missing`, `conflict`
5. Applies updates with backup, skipping user-modified files unless `--force` is used

### CLAUDE.md Management

The kit uses HTML comment sentinels to manage its section:

```markdown
<!-- agent-kit:begin -- managed by agent-workflow-kit, do not edit -->
## Agent Kit Agents
- Pair programming agent: @~/.claude/agents/Ada.md
...
## Agent Kit Workflows
...
## Agent Kit Guidelines
...
<!-- agent-kit:end -->
```

User content outside the sentinels is never touched. The section is cleanly removed on uninstall.

## Development

This project uses [just](https://github.com/casey/just) as a task runner and [uv](https://docs.astral.sh/uv/) for package management.

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [just](https://github.com/casey/just)

### Setup

```bash
git clone https://github.com/mandelbro/agent-workflow-kit.git
cd agent-workflow-kit
uv sync --extra dev
```

### Running locally

```bash
# Run via just
just run -- install --dry-run

# Or directly with uv
uv run agent-kit --help
```

### Commands

```bash
# Run all checks (format, lint, typecheck, test)
just

# Individual commands
just test       # uv run pytest
just lint       # uv run ruff check --fix src/ tests/
just format     # uv run ruff format src/ tests/
just typecheck  # uv run pyright
just coverage   # pytest --cov --cov-fail-under=80
```

### Releasing

Releases are automated via [release-please](https://github.com/googleapis/release-please). On every push to `main`, release-please opens (or updates) a release PR with a changelog derived from [Conventional Commits](https://www.conventionalcommits.org/). Merging that PR triggers a GitHub Release and publishes to PyPI via trusted OIDC publishing.

To publish manually: `Actions > Release > Run workflow` with a git tag (e.g. `v0.2.0`).

### Project Structure

```
src/claude_workflow_kit/
├── cli/
│   ├── app.py          # Typer app entry point (7 commands)
│   ├── install.py      # install / uninstall
│   ├── update.py       # update / diff
│   └── status.py       # status / list / doctor
├── core/
│   ├── config.py       # Pydantic settings (CLAUDE_HOME, derived paths)
│   ├── manifest.py     # Manifest read/write, SHA-256 checksums, file status
│   ├── file_ops.py     # Atomic write, backup, copy, remove, prune empty dirs
│   ├── tdd_outcome.py  # Pydantic model + parser for the tdd-pair headless outcome
│   ├── claude_md.py    # Sentinel-based CLAUDE.md section management
│   └── registry.py     # Asset registry mapping bundled files to targets
└── assets/             # bundled files
    ├── agents/         # 7 agent personas
    ├── skills/         # tdd-pair (SKILL.md, outcome.schema.json, worked-example.md)
    ├── workflows/      # 3 workflow definitions
    ├── guidelines/     # 2 guideline files
    └── coding-principles/  # 1 coding principle
```

## Configuration

The default install target is `~/.claude/`. Override it with:

```bash
# Environment variable
export CLAUDE_HOME=/path/to/custom/dir
agent-kit install

# CLI flag (per command)
agent-kit install --claude-home /path/to/custom/dir
```

## License

[Apache-2.0](LICENSE)
