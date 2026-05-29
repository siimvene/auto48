---
name: skip-ci-commits
description: Suggests appending `[skip ci]` to manual commits in i3/client-deployments when no pipeline run is needed. Use when the agent is preparing a commit message for that repository.
---

# Skip CI for Safe Manual Commits

## Scope

Apply this skill when preparing commit messages for the `i3/client-deployments` repository.

## Core Rule

When committing repository changes that do **not** require an immediate downstream GitLab pipeline run, append ` [skip ci]` to the commit message.

## When to Skip CI

- Manual edits to generated or tracked CI YAML where you are only making maintenance updates.
- Quick fixes, documentation-only commits, or manual tuning after orchestrator runs.
- Any change where you do not explicitly want a pipeline immediately.

## When to NOT Skip CI

- You are intentionally testing the pipeline behavior of a change.
- You are making a change whose only purpose is to adjust deployment flow and you want to observe a run.
- The user explicitly says "run pipeline" or "execute pipeline" with that commit.

## Default Message Pattern

- If the incoming message does not already contain `[skip ci]`, append it.
- Preserve your message content and spacing.
- If message already includes `[skip ci]`, do not duplicate the token.

## Examples

Input: `Update firewall rule for rit/client-saas`
Output: `Update firewall rule for rit/client-saas [skip ci]`

Input: `Update .gitlab-ci.yml for guard path`  
Output: `Update .gitlab-ci.yml for guard path [skip ci]`

Input: `Release: deploy pipeline test (intentional)`  
Output: `Release: deploy pipeline test (intentional)` (no skip token)

## Decision Checklist

- [ ] Repository is `client-deployments`.
- [ ] Commit is manual (not orchestrator automation).
- [ ] No explicit request to run pipeline on this commit.
- [ ] Commit message does not already include `[skip ci]`.
- [ ] Add suffix before committing.

## Reminder

Automated orchestrator commits already include `[skip ci]` in their own scripts.
