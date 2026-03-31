# Task Workflow System

## Purpose

Standardize task implementation with proper tracking and status updates across a distributed task list in the `tasks/` directory.

## Structure

- **Index File** (`tasks/tasks-index.md`): Overall project summary and task file index
- **Task Files** (`tasks/tasks-N.md`): Individual tasks grouped in files of max 10 tasks

## Task Template

```markdown
### Task ID: {ID}

- **Title**: Concise description
- **File**: target/file/path
- **Complete**: [ ]
- **Sprint Points**: 1|2|3|5|8

- **User Story**: As a [role], I want [capability], so that [outcome].
- **Outcome**: What this delivers.

#### Prompt:

Detailed implementation instructions.
```

## Workflow

1. **Locate**: Check `tasks-index.md`, find first task with `Complete: [ ]`
2. **Implement**: Follow the task prompt, write tests first (TDD)
3. **Validate**: Run tests, linter, type checker
4. **Update Status**: Mark `Complete: [x]`, update index counts
5. **Commit**: One commit per completed task
