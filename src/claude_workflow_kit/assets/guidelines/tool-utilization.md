# Tool Utilization Guidelines

## ReAct Framework

For each tool call, follow the ReAct (Reasoning + Acting) cycle:

1. **Reason** — Why do I need this tool? What do I expect to learn?
2. **Act** — Execute the tool call with precise parameters
3. **Observe** — Analyze the result before proceeding
4. **Reflect** — Did I get what I needed? What's the next step?

## Best Practices

- Use dedicated tools over bash equivalents (Read over cat, Grep over grep)
- Batch independent tool calls in parallel
- Read files before editing them
- Search before creating — avoid duplicating existing code
