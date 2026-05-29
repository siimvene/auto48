---
name: tasklist-management
description: Maintain structured Markdown task lists to track implementation progress. Use when creating, updating, or managing task lists in documentation files, or when the user asks about tracking project progress.
---

# Task List Management

Guidelines for creating and managing task lists in markdown files to track project progress.

## Task List Structure

Create task lists in the project docs folder (`docs/implementation-plan.md` or a descriptive name):

```markdown
# Feature Name Implementation

Brief description of the feature and its purpose.

## Completed Tasks

- [x] Task 1 that has been completed
- [x] Task 2 that has been completed

## In Progress Tasks

- [ ] Task 3 currently being worked on
- [ ] Task 4 to be completed soon

## Future Tasks

- [ ] Task 5 planned for future implementation
- [ ] Task 6 planned for future implementation

## Implementation Plan

Detailed description of how the feature will be implemented.

### Relevant Files

- path/to/file1.ts - Description of purpose
- path/to/file2.ts - Description of purpose
```

## Maintenance Rules

1. **Update as you progress**:
   - Mark tasks completed: `[ ]` -> `[x]`
   - Add new tasks as identified
   - Move tasks between sections as appropriate

2. **Keep "Relevant Files" updated** with:
   - File paths created or modified
   - Brief descriptions of each file's purpose
   - Status indicators for completed components

3. **Add implementation details**:
   - Architecture decisions
   - Data flow descriptions
   - Technical components needed
   - Environment configuration

## AI Workflow

1. Regularly update the task list file after implementing significant components
2. Mark completed tasks with `[x]` when finished
3. Add new tasks discovered during implementation
4. Maintain the "Relevant Files" section with accurate paths and descriptions
5. When implementing tasks one by one, first check which task to implement next
6. After implementing a task, update the file to reflect progress

## Example Update

Before:

```markdown
## In Progress Tasks

- [ ] Implement database schema
- [ ] Create API endpoints for data access

## Completed Tasks

- [x] Set up project structure
- [x] Configure environment variables
```

After completing "Implement database schema":

```markdown
## In Progress Tasks

- [ ] Create API endpoints for data access

## Completed Tasks

- [x] Set up project structure
- [x] Configure environment variables
- [x] Implement database schema
```
