# Testing-Driven Development Strategy

## Core Philosophy

Tests define how applications should work, not just confirm how they do work.

## Fundamental Rules

1. **Tests are specifications** — Write them as executable design documents
2. **No workarounds** — Never introduce code just to make tests pass
3. **No shortcuts** — Never delete failing tests to make the build pass
4. **Bug = failing test first** — Reproduce before fixing

## Red-Green-Refactor

1. **Red** — Write the smallest failing test
2. **Green** — Write minimal code to pass
3. **Refactor** — Improve design, keep tests green

## Testing Pyramid

- **Unit tests** (70-80%) — Business logic and algorithms
- **Integration tests** (15-25%) — Service boundaries
- **E2E tests** (5-10%) — Critical user journeys only

## Anti-Patterns to Avoid

- Testing multiple behaviors in one test
- Hidden test dependencies (Mystery Guest)
- Vague assertions (Assertion Roulette)
- Over-mocking internal implementation details
