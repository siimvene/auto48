---
name: code-review
description: Perform structured code reviews and apply clear review findings against project rules and best practices. Use when reviewing code, checking changes before merge, auditing code quality, fixing review findings, or when the user mentions code review, PR review, quality check, or fix what review found.
---

# Code Review Workflow

Systematic review of code changes against workspace rules and best practices.

## When to Use

- User requests a code review
- Feature branch ready for feedback before merge
- Assessing unexpected changes for safety
- User asks to fix, apply, or address findings from a previous code review

## Review Process

### 1. Confirm Scope

- Ask which files/commits to inspect (default: `git diff --name-only HEAD`)
- Note each file's role (source, config, doc, test, infra)

### 2. Collect Applicable Rules

Gather from:
- Always-applied rules
- `.cursor/rules/**/*.mdc`
- Project coding standards
- `AGENTS.md` guidelines

Group into: standards, architecture, framework, performance, security, testing, docs.

### 3. Inspect Each File

For every applicable rule, classify as:
- **Compliant** - meets the standard
- **Partial** - mostly meets, minor issues
- **Non-compliant** - violates the standard

Assign severity:
- **Critical** - security/correctness/data loss
- **High** - significant standard violations or likely bugs
- **Medium** - maintainability, clarity, missing tests
- **Low** - style or minor consistency improvements

### 4. Summarize Findings

Use this format per file:

```markdown
### File: path/to/file.ext

- Overall: Minor issues
- Critical: 0, High: 1, Medium: 2, Low: 0

**Key Findings**
- [High] Architecture – Direct API call from component (rule 010-architecture)
- [Medium] Testing – No regression test for new branch

**Suggested Fixes**
1. Move API call into existing composable
2. Add unit test covering the new edge case
```

Reference the exact rule behind each issue.

### 5. Propose Fixes

- Prioritize by impact (critical → low)
- Keep changes minimal and focused
- Run linters/tests after fixes
- Avoid refactors unless requested

### 6. Close Review

- Deliver final summary with ordered fix list
- Document recurring lessons in `docs/agent-memory.md`
- Label issues as **must-fix** vs **nice-to-have**

## Feedback Format

For each issue, provide:
- **What** - the specific problem
- **Why** - which rule/standard it violates
- **How** - concrete fix with code sample if helpful

## Applying Review Findings

When the user asks to fix, apply, address, or clean up review findings:

1. Prioritize Critical and High findings first.
2. Apply clear Medium and Low fixes when they are local, low-risk, and behavior-preserving.
3. Ask before broad refactors, behavioral changes, API contract changes, or ambiguous tradeoffs.
4. Keep changes minimal and focused on the reviewed diff.
5. After edits, run linting or tests relevant to the changed files.
6. Fix any issues introduced by the review fixes.

## Exit Criteria

Review complete when:
1. Every in-scope file checked against relevant rules
2. Issues documented with severity and references
3. User can clearly decide next actions (fix/defer/approve)
