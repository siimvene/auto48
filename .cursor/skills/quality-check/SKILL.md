---
name: quality-check
description: >-
  Runs the pre-completion quality orchestrator after substantive Agent work:
  simplifier, security-check, code-review, and validation per AGENTS.md or repo
  conventions (any language or build system). Use when the user asks to finish work,
  run quality checks, wrap up a task, or says quality-check. Prefer invoking explicitly
  in Agent mode; not tied to Ask/Debug/Plan.
---

# Quality check (finish-work orchestrator)

Technology-agnostic: applies to any stack (e.g. Node, Python, Go, JVM/Gradle/Maven, .NET). Discovery of formatters, linters, analyzers, and tests follows `AGENTS.md` when present, otherwise the repository’s own docs and config—not a single language’s defaults.

Use this when wrapping **Agent** work that changed code or configuration. If nothing substantive changed, skip invented cleanup and answer normally.

## Orchestrator (run in order)

1. Check whether this turn changed code or configuration. If it did not, do not invent cleanup work; continue to the final response.

2. If files changed, run the **code-simplifier** skill on the touched files to simplify and deslop the implementation while preserving exact behavior.

3. Run the **security-check** skill on the changed files to investigate security problems, permission gaps, data exposure, and abuse paths.

4. Run a full **code-review** skill pass on the changed files against project rules and best practices.

5. Apply clear security-check and code-review findings for correctness, security, standards, and maintainability. Ask before broad refactors, behavior changes, API contract changes, auth model changes, or ambiguous tradeoffs.

6. For validation, follow the **Commands and triggers** in the workspace `AGENTS.md` when present, including any formatters, linters, static analysis, and test commands that file lists in order. If there is no `AGENTS.md`, discover the project’s own entry points: package scripts (`package.json`), `Makefile`, `pyproject.toml` / `tox`, `go test` / `go vet`, Gradle (`./gradlew check`, `test`), Maven, etc. Use **ReadLints** on edited files when the editor reports diagnostics. Run whatever the project uses for **formatting, linting, type or static checks, and tests** (stack-specific: e.g. Black/mypy, `golangci-lint`, Checkstyle/SpotBugs, ESLint/tsc, Pylint, `dotnet format`—match the repo, not a single language). Fix issues introduced by the work when the fix is clear and local.

7. Keep the final response concise: summarize simplification, security fixes, review fixes, validation, and any unresolved findings.
