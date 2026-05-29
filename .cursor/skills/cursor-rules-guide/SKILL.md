---
name: cursor-rules-guide
description: Guide for creating and updating Cursor rule files (.mdc). Use when asked to create a rule, update a rule, or when learning a lesson that should be retained as a new rule.
---

# Cursor Rules Format

## Template Structure

```mdc
---
description: ACTION when TRIGGER to OUTCOME
globs: .cursor/rules/**/*.mdc
alwaysApply: {true or false}
autoAttach: {true or false}
agentRequest: {true or false}
---

# Rule Title

## Context
- When to apply this rule
- Prerequisites or conditions

## Requirements
- Concise, actionable items
- Each requirement must be testable

## Examples
<example>
Good concise example with explanation
</example>

<example type="invalid">
Invalid concise example with explanation
</example>

## Critical Rules
  - Always do X
  - NEVER do Y
```

## File Organization

- **Path**: `.cursor/rules/`
- **Extension**: `.mdc`

### Naming Convention

PREFIX-name.mdc where PREFIX is:

- 0XX: Core standards
- 1XX: Tool configs
- 3XX: Testing standards
- 1XXX: Language rules
- 2XXX: Framework rules
- 8XX: Workflows
- 9XX: Templates
- \_name.mdc: Private rules

### Glob Pattern Examples

- Core standards: .cursor/rules/\*.mdc
- Language rules: src/\*\*/\*.{js,ts}
- Testing standards: \*\*/\*.test.{js,ts}
- React components: src/components/\*\*/\*.tsx
- Documentation: docs/\*\*/\*.mdc
- Configuration files: \*.config.{js,json}
- Multiple extensions: src/\*\*/\*.{js,jsx,ts,tsx}

## Required Fields

### Frontmatter

- **description**: ACTION TRIGGER OUTCOME format
- **globs**: glob pattern for files and folders
- **Activation strategy** (at least one must be specified):
  - `alwaysApply`: Global application, dependent on context relevance
  - `autoAttach`: File-specific activation based on glob patterns
  - `agentRequest`: Explicit invocation during conversations
  - (Manual application is the default when none of the above are true)

### Activation Strategies

| Strategy | When to Use | Examples |
|----------|-------------|---------|
| **alwaysApply: true** | Global standards for all conversations | Code style, architecture, security |
| **autoAttach: true** | File-specific standards via glob matching | Framework patterns, file-type rules |
| **agentRequest: true** | Explicitly invoked during conversations | Specialized workflows, complex patterns |
| **Manual** (default) | Only when explicitly requested by user | Project-specific guidelines, optional patterns |

### Body

- context: Usage conditions
- requirements: Actionable items
- examples: Both valid and invalid
- critical-rules: Summary of most critical rule bullets

## Formatting Guidelines

- Use concise Markdown primarily
- XML tags limited to: `<example>`, `<danger>`, `<required>`
- Always indent content within XML or nested XML tags by 2 spaces
- Emojis and Mermaid diagrams allowed if they better explain the rule
- Reference files using: `[filename.ext](mdc:path/to/filename.ext)`

## Critical Rules

- Keep frontmatter description under 120 characters with clear intent for AI selection
- Keep rules DRY -- no repetition or redundant explanations
- Frontmatter MUST have description, globs, and at least one activation strategy
- Use standard glob patterns without quotes
- Target under 50 lines total (under 25 is better), unless diagrams or examples require more
- Always include both valid and invalid examples
- Choose activation strategy based on the rule's purpose and scope
