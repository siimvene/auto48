---
name: security-check
description: Investigate changed code like a red-team reviewer for security bugs, permission gaps, data exposure, and abuse paths. Use when reviewing security, checking permissions, auditing auth or access control, or when the user mentions security-check, red team, pen test, vulnerability, permission gap, or security audit.
---

# Security Check

Thoroughly investigate the current feature for security problems and permission gaps. Think like a red-team tester, then suggest or apply focused fixes.

## When to Use

- User asks for a security review, security audit, red-team pass, or pen-test style assessment.
- User asks to check permissions, access control, auth, sensitive data, or trust boundaries.
- A finish-work workflow needs a security pass on changed files.

## Scope

- Prefer files changed in the current session.
- If session scope is unclear, inspect `git diff` and `git diff --cached`.
- For branch-level audits without a narrower scope, compare against `main`.
- Include adjacent code only when needed to understand trust boundaries or permissions.

## Security Checklist

Look for exploitable issues and missing defenses:

- Authorization gaps, role bypasses, provider/tenant isolation bugs, and insecure direct object references.
- Authentication assumptions, session handling mistakes, token leaks, and unsafe redirects.
- Server/client trust boundary mistakes, especially client-side checks used as the only enforcement.
- Input validation gaps, unsafe parsing, injection risks, and unsanitized user-controlled data.
- XSS, HTML injection, unsafe URL handling, and unsafe rendering of localized or rich text.
- Sensitive data exposure in UI, logs, errors, network payloads, or persisted state.
- CSRF, CORS, cookies, security headers, and server-side or middleware defaults that weaken protection.
- File upload, media, or external URL handling risks.
- Dependency, generated SDK, or API contract changes that alter the security model.

## Project security rules (when present)

Before judging the diff, load the workspace’s own security standards and align findings to them—language- and stack-agnostic paths vary, for example:

- Cursor rules: `.cursor/rules/**/*security*.mdc` (or numbered equivalents such as `050-security.mdc`)
- Repo docs: `AGENTS.md`, `docs/security.md`, or security sections in `CONTRIBUTING.md`

If none exist, rely on the checklist below and general secure-design practice.

## Workflow

1. Identify the changed files and relevant trust boundaries.
2. Read project security rules (see **Project security rules** above), plus architecture or “known mistakes” docs when present.
3. Trace realistic abuse paths, not just type or style issues.
4. Classify findings by severity: Critical, High, Medium, Low.
5. Apply clear, local, behavior-preserving security fixes when requested by the workflow.
6. Ask before broad refactors, API contract changes, auth model changes, or ambiguous product/security tradeoffs.
7. Run relevant validation for edited files.

## Reporting

Lead with security findings, ordered by severity. For each finding, include:

- **What**: the vulnerable behavior or permission gap.
- **Why**: the exploit or data exposure risk.
- **How**: the focused fix or mitigation.

If no issues are found, say so and note any residual risk or validation gap.
