# Discovery: agent-workflow-kit

**Date**: 2026-03-30
**Author**: Norwood (Discovery & Planning Agent)
**Status**: Draft

---

## The One-Liner

A Python CLI that packages, installs, and manages a bespoke Claude Code subagent and workflow system -- the opinionated workflow layer that sits on top of awesome-claude-hooks.

## The Problem

You have built a sophisticated Claude Code operating environment across two categories of files: **runtime hooks** (bash scripts that intercept Claude Code tool calls in real time) and **knowledge assets** (markdown agent personas, workflow definitions, guidelines, and templates that shape how Claude Code thinks and operates). The hooks live in a proper repo with an installer. The knowledge assets are scattered across `~/.claude/agents/` and `~/.claude/knowledge/` with no installation story, no versioning, and no way to share them with other developers.

Right now, setting up this workflow system on a new machine means manually copying 15+ files into the right directories, editing `~/.claude/CLAUDE.md` to add `@` references, and hoping you remember which version of Norwood.md is the current one. That is untenable for a system you intend to publish, and it is fragile even for personal use.

## The Solution

Build `agent-workflow-kit` as a standalone Python CLI (installed via `pipx`) that manages the full lifecycle of knowledge assets: install, update, customize, and uninstall. It treats `awesome-claude-hooks` as a peer dependency -- the two projects complement each other but remain independent repos with independent installers.

## The Work

- **Effort**: ~5 days of focused development (40 story points across 4 phases)
- **Timeline**: 2 weeks including testing and documentation
- **Team Needs**: Solo developer, Python 3.12+, existing Typer/Rich expertise

## The Risks

1. **CLAUDE.md merge corruption** -- Programmatic edits to a user-maintained markdown file risk clobbering content. Mitigated by sentinel-based section management.
2. **Upstream drift** -- Users customize agent personas, then upstream updates arrive. Mitigated by a diff-and-prompt strategy rather than blind overwrites.
3. **Path assumptions** -- Hardcoding `~/.claude/` may conflict with future Claude Code configuration changes. Mitigated by a single `CLAUDE_HOME` config variable.

---

## Phase 0: Initial Context

### What problem are we solving?

The user has 12 agent personas, 6 workflow definitions, 3 guideline files, and a CLAUDE.md integration layer. None of these have an automated installation path. They need to be packaged into an installable, updatable, and customizable distribution.

### What exists already?

| Asset | Location | Count | Purpose |
|-------|----------|-------|---------|
| Agent personas | `~/.claude/agents/*.md` | 12 files (6 core) | Shape Claude Code behavior per role |
| Workflows | `~/.claude/knowledge/workflows/*.md` | 6 files (3 core) | Task management, retros, project init |
| Guidelines | `~/.claude/knowledge/*.md` | 3 files | File optimization, tool usage, TDD |
| Coding principles | `~/.claude/knowledge/coding-principles/*.md` | 3 files | Testing strategy, frontend dev, e2e |
| CLAUDE.md | `~/.claude/CLAUDE.md` | 1 file | Central `@` reference hub |
| awesome-claude-hooks | Separate git repo | 11 hooks + installer | Runtime behavior enforcement |

### What constraints are we working with?

1. **awesome-claude-hooks is mature and bash-native.** Its installer works. Do not propose absorbing it into a Python project.
2. **Target audience is Claude Code power users** who are comfortable with `pipx install` but should not need to understand the internal file layout.
3. **macOS and Linux support required.** Windows is nice-to-have but not blocking.
4. **`~/.claude/` is the canonical installation target.** Claude Code reads from this directory.
5. **User customizations must survive upgrades.** If someone tweaks Norwood.md, a blind overwrite is unacceptable.

---

## Phase 1: Code Archaeology

### 1.1 awesome-claude-hooks Installer Analysis

The existing `install.sh` (173 lines) is a well-structured bash installer that handles:

- **Prerequisites**: Validates `jq` and bash 3.2+
- **Backup**: Timestamps and preserves existing hooks before overwrite
- **File copy**: Iterates `hooks/*.sh` into `~/.claude/hooks/`, prompts before overwrite (unless `--force`)
- **Settings merge**: Uses a sophisticated `jq` pipeline to append hook entries to `~/.claude/settings.json` without duplicating existing entries
- **Post-install tests**: Runs `tests/run-tests.sh` automatically
- **Flags**: `--force`, `--dry-run`, `--hooks-only`

The uninstaller (94 lines) reverses the process, targeting only known hook filenames and cleaning settings.json entries that reference `~/.claude/hooks/`.

**Key reuse insight**: The settings.json merge strategy (lines 121-130 of install.sh) is the most sophisticated part. The workflow kit does NOT need to touch settings.json -- it only manages markdown files and CLAUDE.md references. This is a clean separation of concerns.

### 1.2 Knowledge Asset Analysis

The files that `agent-workflow-kit` needs to manage fall into clear categories:

**Core agents (ship with the kit):**
- `Norwood.md` (651 lines) -- Discovery and planning
- `Eco.md` (410 lines) -- Research with Firecrawl
- `Ive.md` (122 lines) -- UX design
- `Zod.md` (288 lines) -- Technical review
- `Shelly.md` (296 lines) -- Task generation and sprint pointing
- `Ada.md` (139 lines) -- Pair programming persona

**Extended agents (user has more, but these are personal):**
- `Arendt.md`, `Conway.md`, `Hans.md`, `Morgan.md`, `Orwell.md`, `Roy.md`

**Core workflows:**
- `tasks-workflow.md` (319 lines) -- Task management system
- `retro.md` (45 lines) -- Retrospective process
- `project-initialization.md` (754 lines) -- New project setup

**Core guidelines:**
- `file-and-context-optimization.md` (178 lines)
- `tool-utilization.md` (21 lines)
- `testing-strategy.md` (in `coding-principles/`)

**CLAUDE.md integration:**
The existing `~/.claude/CLAUDE.md` (274 lines) contains `@` references that point to these files. The kit needs to inject and manage a section of these references without disturbing user-authored content.

### 1.3 Existing Components & Reuse Plan

| Component | Reuse? | Rationale |
|-----------|--------|-----------|
| autopilot-cli's Typer + Rich + Pydantic stack | **Yes** | Proven stack, developer already proficient |
| autopilot-cli's `pyproject.toml` structure | **Yes** | Use as template for project scaffolding |
| awesome-claude-hooks `install.sh` | **No** | Different concern (hooks vs knowledge), keep independent |
| awesome-claude-hooks backup strategy | **Yes, pattern** | Same timestamped-backup approach for knowledge files |
| awesome-claude-hooks `--force`/`--dry-run` flags | **Yes, pattern** | Same UX conventions for consistency |
| `jq` settings.json merge logic | **No** | Agent kit does not touch settings.json |

---

## Phase 2: Solution Architecture

### ADR-001: CLI Framework Selection

#### The Situation

We need a Python CLI framework to build the installer/manager. The user already has Typer expertise from autopilot-cli, but we should evaluate alternatives from the awesome-cli-frameworks list.

#### Options Evaluated

**1. Typer (tiangolo/typer)**
- Pros: User already knows it, FastAPI-style type hints, Rich integration built-in, excellent for subcommand-heavy CLIs, active maintenance, strong community
- Cons: Runtime dependency on Click (abstraction layer adds weight)
- Effort: Minimal learning curve -- reuse patterns from autopilot-cli

**2. Click (pallets/click)**
- Pros: Industry standard, battle-tested, highly composable, no wrapper overhead
- Cons: More verbose decorator syntax, user would need to context-switch from Typer patterns
- Effort: Moderate -- different patterns than autopilot-cli

**3. Python-Fire (google/python-fire)**
- Pros: Zero-config CLI from any Python object, extremely fast to prototype
- Cons: Poor control over help text, no built-in validation, not great for complex subcommands
- Effort: Low initial, high for polish

**4. Cyclopts (BrianPugh/cyclopts)**
- Pros: Modern type-hint-based approach, similar philosophy to Typer
- Cons: Smaller community, less battle-tested, unfamiliar to the user
- Effort: Moderate learning curve

**5. Cement (datafolklabs/cement)**
- Pros: Full application framework with config, logging, plugins
- Cons: Heavyweight for this use case, opinionated structure, overkill
- Effort: High -- learning the framework conventions

**6. argparse (stdlib)**
- Pros: Zero dependencies, ships with Python
- Cons: Verbose, no rich output, no type-hint integration, boilerplate-heavy
- Effort: High for equivalent UX

**7. Plac (ialbert/plac)**
- Pros: Minimal boilerplate, function-signature-based
- Cons: Limited subcommand support, small community, not actively maintained
- Effort: Low initial, poor scalability

#### Decision: Typer + Rich + Pydantic v2

This is not a close call. The user has production experience with this exact stack in autopilot-cli. Typer gives us subcommands with type-hint validation. Rich gives us beautiful terminal output (progress bars during install, diff tables during update). Pydantic gives us configuration validation. Choosing anything else would mean learning a new framework to build functionally the same thing.

#### Trade-offs Accepted

- Typer wraps Click, adding ~2MB to the installed package. Acceptable for a tool installed via `pipx`.
- We are coupling to tiangolo's maintenance cadence. Typer v0.15+ is stable and Click compatibility is mature.

---

### ADR-002: Relationship to awesome-claude-hooks

#### The Situation

Should agent-workflow-kit absorb awesome-claude-hooks into a monorepo, extend it, or remain independent?

#### Options Considered

**1. Monorepo (merge both projects)**
- Pros: Single install command, unified versioning
- Cons: Mixes bash and Python toolchains, forces Python on users who only want hooks, complicates the existing hooks repo's contributor story, breaks existing install docs

**2. Plugin relationship (workflow-kit extends hooks)**
- Pros: Single entry point
- Cons: Creates a hard dependency where none is needed. The hooks work without the workflow kit and vice versa.

**3. Peer projects (independent repos, documented together)**
- Pros: Clean separation of concerns, each project has its own lifecycle, users can adopt either or both, no forced dependencies
- Cons: Two install commands instead of one

#### Decision: Peer Projects

The hooks and the workflow kit solve different problems with different tools. Hooks intercept Claude Code tool calls in real time using bash. The workflow kit manages static knowledge files using Python. Coupling them would create a project that is harder to maintain, harder to contribute to, and harder to adopt incrementally.

The README for each project will cross-reference the other. A user who installs both gets the full experience. A user who only wants hooks gets hooks. A user who only wants the agent system gets the agent system.

#### Trade-offs Accepted

- Users must run two installers for the complete setup. We will document the combined install path clearly.
- Version coordination is manual. If a workflow update assumes a new hook exists, the README must note the minimum hooks version.

---

### ADR-003: File Management Strategy

#### The Situation

How should the CLI place files into `~/.claude/`? Options: direct copy, symlinks, or git submodules.

#### Options Considered

**1. Direct copy (cp)**
- Pros: Simple, no hidden dependencies, files are self-contained, works on all filesystems
- Cons: Updates require re-running install, no automatic sync

**2. Symlinks (ln -s)**
- Pros: Changes to source propagate automatically, good for dev workflow
- Cons: Breaks if source moves, iCloud Drive symlinks are fragile, requires the source repo to stay cloned, confuses users who expect files at the target path

**3. Git submodule**
- Pros: Version-pinned, reproducible
- Cons: Requires git expertise, submodule UX is universally despised, overkill for markdown files

#### Decision: Direct Copy with Manifest Tracking

Files are copied into `~/.claude/`. A manifest file (`~/.claude/.workflow-kit/manifest.json`) tracks what was installed, when, and from which version. This enables `update` and `uninstall` commands to know exactly which files belong to the kit.

```json
{
  "version": "0.1.0",
  "installed_at": "2026-03-30T12:00:00Z",
  "files": [
    {
      "source": "agents/Norwood.md",
      "target": "~/.claude/agents/Norwood.md",
      "checksum": "sha256:abc123...",
      "modified_by_user": false
    }
  ]
}
```

#### Trade-offs Accepted

- Users must run `agent-kit update` to get new versions. This is intentional -- automatic sync would risk overwriting customizations.

---

## Phase 3: Technical Deep Dives

### 3.1 CLAUDE.md Merge Strategy

This is the hardest problem in the project. The user's `~/.claude/CLAUDE.md` is a hand-maintained file. We need to inject `@` references without clobbering existing content.

**Approach: Sentinel-Bounded Sections**

```markdown
<!-- agent-kit:begin — managed by agent-workflow-kit, do not edit -->
## Agent Kit Agents

When performing discovery and planning, use @~/.claude/agents/Norwood.md
When performing research, use @~/.claude/agents/Eco.md
...

## Agent Kit Knowledge

Review the task workflow system in @~/.claude/knowledge/workflows/tasks-workflow.md
...
<!-- agent-kit:end -->
```

The install command:
1. Reads the existing CLAUDE.md
2. Checks for existing sentinel markers
3. If found, replaces the content between markers
4. If not found, appends the managed section at the end
5. Writes the file atomically (write to temp, then rename)

The uninstall command:
1. Reads CLAUDE.md
2. Removes everything between sentinels (inclusive)
3. Writes the file atomically

**Edge cases handled:**
- File does not exist: Create it with only the managed section
- File exists but is empty: Write the managed section
- Sentinels exist but are malformed: Warn and append a fresh section
- User has their own `@` references outside the managed section: Untouched

### 3.2 Version Management and Update Strategy

When the user runs `agent-kit update`, three scenarios can occur for each managed file:

| Upstream Changed | User Modified | Action |
|-----------------|---------------|--------|
| No | No | Skip (already current) |
| Yes | No | Overwrite silently |
| Yes | Yes | Show diff, prompt for resolution |

Detection relies on the manifest's checksum field:

```python
def check_file_status(manifest_entry: FileEntry) -> FileStatus:
    target = Path(manifest_entry.target).expanduser()
    if not target.exists():
        return FileStatus.MISSING

    current_hash = sha256(target.read_bytes())
    if current_hash == manifest_entry.checksum:
        return FileStatus.UNMODIFIED  # user hasn't touched it

    return FileStatus.USER_MODIFIED  # user has local changes
```

For the conflict case (upstream changed AND user modified), the CLI:
1. Shows a Rich-formatted side-by-side diff
2. Offers three choices: accept upstream, keep local, or save upstream as `.new` for manual merge
3. Records the user's decision in the manifest

### 3.3 CLI Command Design

```
agent-kit install [--force] [--dry-run] [--skip-claude-md]
agent-kit update [--force] [--check-only]
agent-kit uninstall [--keep-files] [--dry-run]
agent-kit status
agent-kit list [agents|workflows|guidelines]
agent-kit diff <file>
agent-kit doctor
```

**`agent-kit install`** -- First-time setup. Copies all managed files into `~/.claude/`, creates the manifest, and injects the CLAUDE.md section. With `--force`, overwrites without prompting. With `--dry-run`, shows what would happen.

**`agent-kit update`** -- Checks for upstream changes (compares bundled files against installed copies). Handles conflicts per the strategy above. With `--check-only`, reports status without modifying anything.

**`agent-kit uninstall`** -- Removes managed files and the CLAUDE.md section. With `--keep-files`, only removes the manifest and CLAUDE.md section (leaves the actual files in place).

**`agent-kit status`** -- Shows a Rich table of all managed files with their status: installed, modified, missing, outdated.

**`agent-kit list`** -- Lists available agents, workflows, or guidelines with descriptions.

**`agent-kit diff <file>`** -- Shows the diff between the installed version and the bundled (upstream) version.

**`agent-kit doctor`** -- Validates the installation: checks that all managed files exist, CLAUDE.md references are correct, and the manifest is consistent. Mirrors the `--doctor` pattern from autopilot-cli.

### 3.4 Package Structure

```
agent-workflow-kit/
  pyproject.toml
  src/
    claude_workflow_kit/
      __init__.py
      cli/
        app.py          # Typer app with command groups
        install.py      # install/uninstall commands
        update.py       # update/diff commands
        status.py       # status/list/doctor commands
      core/
        manifest.py     # Manifest read/write/checksum logic
        file_ops.py     # Copy, backup, atomic write operations
        claude_md.py    # CLAUDE.md sentinel merge logic
        config.py       # Pydantic settings (CLAUDE_HOME, etc.)
      assets/
        agents/         # Bundled agent persona markdown files
          Norwood.md
          Eco.md
          Ive.md
          Zod.md
          Shelly.md
          Ada.md
        workflows/
          tasks-workflow.md
          retro.md
          project-initialization.md
        guidelines/
          file-and-context-optimization.md
          tool-utilization.md
        coding-principles/
          testing-strategy.md
        templates/
          claude-md-section.md.jinja2
  tests/
    test_manifest.py
    test_file_ops.py
    test_claude_md.py
    test_install.py
    test_update.py
  justfile
```

Assets are bundled inside the Python package using `importlib.resources` (Python 3.9+). This means `pipx install agent-workflow-kit` gives users everything -- no separate clone required.

### 3.5 Customization Strategy

Users will want to modify agent personas. The kit should support this without creating friction during updates.

**Approach: "Don't fight the user."**

1. After install, all files are plain markdown in `~/.claude/`. Users edit them directly.
2. The manifest tracks whether the user has modified each file (via checksum comparison).
3. On `agent-kit update`, modified files are never silently overwritten.
4. Users who want to reset a file to upstream can run `agent-kit update --force` or delete the file and re-run `agent-kit install`.

**What about user-only agents?** The extended agents (Arendt, Conway, Hans, Morgan, Orwell, Roy) are not bundled. Users manage those independently. The kit only manages its declared manifest of core files.

---

## Phase 4: Risk Analysis

### High Risk: CLAUDE.md Corruption

**Probability**: Medium (sentinel parsing is straightforward but edge cases exist)
**Impact**: High (broken CLAUDE.md means Claude Code loses all workflow context)
**Mitigation**: Atomic writes (temp file + rename). Backup before every modification. Validate markdown structure after write. The `agent-kit doctor` command detects corruption.
**Detection**: `agent-kit doctor` validates sentinel integrity on every run.

### Medium Risk: Path Assumption Fragility

**Probability**: Low (Claude Code has used `~/.claude/` since launch)
**Impact**: Medium (if Anthropic changes the path, everything breaks)
**Mitigation**: Single `CLAUDE_HOME` environment variable override. All path construction goes through `config.py`. If Claude Code ever moves, one config change fixes it.
**Detection**: `agent-kit doctor` verifies that `CLAUDE_HOME` exists and is writable.

### Medium Risk: Large File Bundling

**Probability**: Certain (the asset files total ~8,000 lines)
**Impact**: Low (adds ~200KB to the pip package, negligible)
**Mitigation**: None needed. Markdown compresses well, and `pipx` installs are not size-sensitive.
**Detection**: N/A

### Low Risk: Cross-Platform Path Handling

**Probability**: Low on macOS/Linux, medium on Windows
**Impact**: Medium (tilde expansion, path separators)
**Mitigation**: Use `pathlib.Path.expanduser()` everywhere. Test on both macOS and Linux in CI. Windows support is documented as best-effort.
**Detection**: CI matrix with macOS and Ubuntu runners.

### Low Risk: Dependency on Typer Maintenance

**Probability**: Low (Typer 0.15+ is stable, backed by tiangolo's track record)
**Impact**: Low (Click remains the fallback; migration would be straightforward)
**Mitigation**: Pin `typer>=0.15,<1.0` to avoid breaking changes.
**Detection**: Dependabot alerts.

---

## Phase 5: Implementation Plan

### Phase 1: Foundation (13 points, ~2 days)

| Task | Points | Description |
|------|--------|-------------|
| Project scaffolding | 2 | pyproject.toml, src layout, justfile, CI skeleton |
| Config module | 2 | Pydantic settings with CLAUDE_HOME, manifest path |
| Manifest module | 3 | Read/write/checksum manifest.json, file status enum |
| File operations module | 3 | Copy with backup, atomic write, directory creation |
| CLAUDE.md merge module | 3 | Sentinel detection, section injection/removal, Jinja2 template |

**Success criteria**: All core modules have passing tests. No CLI yet -- this is the engine.

### Phase 2: CLI Commands (13 points, ~2 days)

| Task | Points | Description |
|------|--------|-------------|
| Typer app scaffold | 2 | App with command groups, Rich console setup |
| `install` command | 3 | Full install flow with --force, --dry-run, --skip-claude-md |
| `uninstall` command | 2 | Reverse install with --keep-files |
| `update` command | 3 | Checksum comparison, conflict resolution, Rich diff display |
| `status` / `list` / `doctor` | 3 | Rich tables, validation checks, asset listing |

**Success criteria**: All commands work end-to-end in a tmp directory. Integration tests pass.

### Phase 3: Asset Bundling & Polish (8 points, ~1 day)

| Task | Points | Description |
|------|--------|-------------|
| Bundle core assets | 2 | Copy 6 agents, 3 workflows, 3 guidelines into src/assets/ |
| CLAUDE.md template | 2 | Jinja2 template for the managed section |
| Cross-platform testing | 2 | CI matrix: macOS 14, Ubuntu 24.04, Python 3.12/3.13 |
| Error handling polish | 2 | Rich error panels, graceful failures, help text |

**Success criteria**: `pipx install .` works on a clean macOS machine with no prior `~/.claude/` setup.

### Phase 4: Documentation & Release (6 points, ~1 day)

| Task | Points | Description |
|------|--------|-------------|
| README with quick start | 2 | Install, usage, relationship to awesome-claude-hooks |
| Combined setup guide | 2 | Document the hooks + workflow-kit full setup |
| PyPI release automation | 2 | GitHub Actions: test, build, publish to PyPI |

**Success criteria**: A new user can go from zero to fully configured in under 5 minutes following the README.

---

## Technical Specification

### Dependencies

```toml
[project]
dependencies = [
    "typer>=0.15,<1.0",
    "rich>=13.0",
    "pydantic>=2.10",
    "pydantic-settings>=2.2",
    "jinja2>=3.1",
]
```

No runtime dependency on `jq`, `git`, or any external binary. Pure Python.

### Entry Point

```toml
[project.scripts]
agent-kit = "claude_workflow_kit.cli.app:app"
```

### Minimum Python Version

Python 3.12+ (consistent with autopilot-cli, leverages `importlib.resources` improvements).

### Key Implementation Details

**Atomic file writes:**
```python
def atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically via temp file + rename."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.rename(path)
```

**Sentinel-based CLAUDE.md merge:**
```python
SENTINEL_BEGIN = "<!-- agent-kit:begin -- managed by agent-workflow-kit, do not edit -->"
SENTINEL_END = "<!-- agent-kit:end -->"

def inject_section(claude_md: str, section: str) -> str:
    """Replace or append the managed section in CLAUDE.md."""
    begin_idx = claude_md.find(SENTINEL_BEGIN)
    end_idx = claude_md.find(SENTINEL_END)

    managed_block = f"{SENTINEL_BEGIN}\n{section}\n{SENTINEL_END}\n"

    if begin_idx != -1 and end_idx != -1:
        # Replace existing managed section
        return claude_md[:begin_idx] + managed_block + claude_md[end_idx + len(SENTINEL_END) + 1:]

    # Append to end
    separator = "\n\n" if claude_md and not claude_md.endswith("\n\n") else ""
    return claude_md + separator + managed_block
```

**Manifest checksum for user-modification detection:**
```python
def file_checksum(path: Path) -> str:
    """SHA-256 hex digest of file contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
```

---

## Relationship Summary

```
awesome-claude-hooks (bash)          agent-workflow-kit (Python)
==========================          ============================
Manages: ~/.claude/hooks/*.sh       Manages: ~/.claude/agents/*.md
         ~/.claude/settings.json             ~/.claude/knowledge/**/*.md
                                             ~/.claude/CLAUDE.md (section)

Install: bash install.sh            Install: pipx install agent-workflow-kit
                                             agent-kit install

Concern: Runtime hook enforcement   Concern: Knowledge asset management
```

These are two projects that serve the same user but solve different problems. A user who wants both runs:

```bash
# Install hooks (bash)
git clone git@github.com:mandelbro/awesome-claude-hooks.git
cd awesome-claude-hooks && bash install.sh --force

# Install workflow kit (Python)
pipx install agent-workflow-kit
agent-kit install
```

Five minutes. Full setup. No conflicts.

---

## Quality Gates

- [ ] Problem clearly defined
- [ ] Current implementation analyzed with code references
- [ ] Multiple solutions proposed with trade-offs (3 ADRs)
- [ ] Recommendation made with reasoning
- [ ] Implementation plan detailed with 4 phases
- [ ] Risks identified with mitigations (5 risks)
- [ ] Success metrics defined (per-phase criteria)
- [ ] Code examples provided (atomic write, sentinel merge, checksum)
- [ ] Existing Components & Reuse Plan completed
- [ ] Rule-of-Three consolidation evaluated (N/A -- greenfield project)

### The Drunk Test
Could a slightly drunk engineer understand this? Yes -- install agents with `agent-kit install`, update them with `agent-kit update`, check health with `agent-kit doctor`.

### The Future Test
Will we understand this in 6 months? Yes -- the manifest.json provides a complete audit trail of what was installed and when.

### The Handoff Test
Could another team implement this without asking questions? Yes -- the ADRs explain every decision, the package structure is explicit, and the implementation plan has concrete deliverables per phase.

### The Reality Test
Are the estimates realistic? 40 story points across 4 phases for a developer who already has Typer/Rich/Pydantic expertise and a reference implementation in autopilot-cli. This is realistic for 2 weeks of calendar time with other obligations.
