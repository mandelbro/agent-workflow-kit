# File and Context Optimization Guidelines

## File Size Targets

- **Target range**: 100-500 lines per file
- **Hard limit**: Never exceed 1,000 lines without architectural justification
- **Evaluation trigger**: When a file approaches 400 lines, evaluate for splitting

## Principles

1. **Single Responsibility** — Each file should have ONE clear, focused purpose
2. **Logical Separation** — Split by functionality, not arbitrary line counts
3. **Modular Design** — Break complex classes into smaller, focused components
4. **Clear Naming** — Use descriptive names that indicate file purpose

## When to Split

- File exceeds 400 lines
- File contains multiple unrelated classes or functions
- File has mixed concerns (UI + business logic, data access + validation)
- File changes frequently for different reasons

## How to Split

1. Extract utility functions to separate files
2. Move related classes to dedicated modules
3. Separate concerns into logical boundaries
4. Create index files for clean imports
5. Never split arbitrarily — maintain logical cohesion
