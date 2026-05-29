---
name: code-simplifier
description: Simplify and deslop recently modified code while preserving exact behavior. Use when cleaning up AI-generated code, simplifying recent changes, applying review fixes, or when the user mentions code-simplifier, deslop, AI slop, cleanup, simplify, or make code cleaner.
---

# Code Simplifier

Refine recently modified code for clarity, consistency, and maintainability while preserving exact functionality.

## When to Use

- User asks to simplify, clean up, deslop, or improve recent changes.
- User asks to apply review feedback and make the result cleaner.
- User mentions AI slop, `code-simplifier`, or making generated code more human.
- A finishing workflow needs final cleanup before the agent stops.

If `code-review` was already run on the same changes, do not repeat a full audit. Focus on applying clear fixes and simplifying the code.

## Scope

- Prefer recently modified files from the current session.
- If session scope is unclear, inspect `git diff` and `git diff --cached`.
- For branch-level cleanup without a narrower scope, compare against `main`.
- Do not modify unrelated files or revert user changes.

## Simplification Checklist

Preserve behavior exactly while improving the implementation:

- Remove obvious comments that narrate the code. Preserve useful JSDoc, docstrings, and comments explaining non-obvious constraints.
- Remove unnecessary defensive checks on trusted or already validated code paths.
- Remove redundant null checks where types guarantee a value is present.
- Replace `any` casts and unnecessary `unknown` types with proper types when the correct type is clear.
- Remove wrapper functions, abstractions, or variables that add no clarity.
- Use one semantic name for one concept across touched code.
- Reduce unnecessary nesting and duplicated logic.
- Deduplicate local code only when doing so reduces complexity and improves readability.
- Remove unused code only after verifying it is not referenced.
- Remove stale legacy, fallback, stub, or in-progress code paths in touched files when they are clearly no longer needed.
- Avoid nested ternaries. Prefer clear `if`/`else` chains or `switch` statements.
- Prefer explicit, readable code over compact or clever code.
- Follow local project patterns, existing helpers, and `.cursor/rules/` standards.

## Workflow

1. Identify the changed files and the intent of the current work.
2. Read the surrounding code before editing.
3. Apply small, behavior-preserving refinements.
4. Keep helpful abstractions that organize real complexity.
5. Run linting or the closest available validation for edited files.
6. Fix any lint errors introduced by the cleanup.
7. Summarize the cleanup in 1-3 sentences.

## Guardrails

- Stay within scope: do not refactor, reformat, or “clean up” code you did not need to touch for the current session’s change.
- Prefer removing unused imports, variables, or helpers **your** edits made redundant; leave unrelated pre-existing dead code alone unless asked or explicitly in scope.
- Do not broaden the task into unrelated refactors.
- Do not optimize for fewer lines at the cost of clarity.
- Do not change public behavior, data shapes, API contracts, or persisted formats.
- Do not add compatibility layers for unshipped in-progress code unless explicitly needed.
- Ask before making risky architectural changes.
