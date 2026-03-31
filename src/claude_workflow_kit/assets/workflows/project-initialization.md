# Project Initialization Workflow

## Purpose

Set up a new project with consistent structure, tooling, and documentation.

## Steps

### 1. Discovery
- Define the problem and solution scope
- Use the Norwood agent for discovery and planning
- Save discovery document to `docs/discovery/`

### 2. Project Structure
- Create standard directory layout (`src/`, `tests/`, `docs/`, `config/`)
- Set up build system (`pyproject.toml` or `package.json`)
- Configure linting, formatting, and type checking
- Set up test framework

### 3. Task Generation
- Use the Shelly agent to generate tasks from the discovery document
- Create `tasks/tasks-index.md` and `tasks/tasks-1.md`
- Estimate sprint points for all tasks

### 4. Sprint Planning
- Select tasks for the first sprint (max 15 points per PR)
- Create sprint record in `docs/project-management/sprints/`
- Begin implementation following TDD workflow

## Deliverables

- Project scaffolding with all tooling configured
- Discovery document in `docs/discovery/`
- Task files in `tasks/` directory
- First sprint record
